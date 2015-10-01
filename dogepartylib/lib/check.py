import json
import requests
import logging
logger = logging.getLogger(__name__)
import warnings
import time
import sys

from dogepartylib.lib import config
from dogepartylib.lib import util
from dogepartylib.lib import exceptions
from dogepartylib.lib import backend
from dogepartylib.lib import database

CONSENSUS_HASH_SEED = 'We can only see a short distance ahead, but we can see plenty there that needs to be done.'

CONSENSUS_HASH_VERSION_MAINNET = 2
CHECKPOINTS_MAINNET = {
    config.BLOCK_FIRST_MAINNET: {'ledger_hash': '766ff0a9039521e3628a79fa669477ade241fc4c0ae541c3eae97f34b547b0b7', 'txlist_hash': '766ff0a9039521e3628a79fa669477ade241fc4c0ae541c3eae97f34b547b0b7'},
    336000: {'ledger_hash': 'ebe9bae9e0d6ef4f7ef729ecba28b8f4f9829e2303733f1ff6ef649c9b7556c8', 'txlist_hash': 'a38eb029943f563fa8cb2a1447d23b46a5b8608a5ef06e63091526680bd969f1'},
    337000: {'ledger_hash': '4cd7586c934d8f9a839e8a010cf0023e0971db34cd138d454b60a7d0d222032f', 'txlist_hash': '20f01e01b7a7456a13b89bc49d6493a0b052ad98fb9c7f2ea5d953d6c600622f'},
    338000: {'ledger_hash': '78e947190c76bf3a5156d47e098871241b8710694f5f71f2b7d0b9db9adb9dd7', 'txlist_hash': '306204d22f4e8ee7db619d97cb151587e3dd050f27605c1d4b22a4d8877b4305'},
    339000: {'ledger_hash': '8502d024910ef6a3b15fe558e94867d80bf9d84dda1e5e6cb4b8c4b22b48facd', 'txlist_hash': '942bd83baa1762904e78be18f0ef6a7c24481a6aed28ff50ca40dbaa789d6231'},
    340000: {'ledger_hash': 'b5ea99ad882bd783284885fea6888be945ec8879ec57755d2e5737eff4b43877', 'txlist_hash': 'f951cf5a74676e0da578422e10f569fcafed0aa76a7d8df09e9c67ab5befbb8f'},
    341000: {'ledger_hash': '84392b52170301c4070aaef21419a95a9ab32a8804850faedd662524db66ac93', 'txlist_hash': '9bca3e0ddce1005a3f8ffd5c938ebb2b3e9ce6446595e0ed2f96e71cfb10144b'},
    342000: {'ledger_hash': '8dd6ed3c3540ab07a672652b102971bbe157d653c97853610c3ad29422841671', 'txlist_hash': '3afeb4768fd6d3b10b7576d2bb2c502ac4a8bb854d1660708dedb7b243d504c7'},
    343000: {'ledger_hash': 'a1b11782a2c784dc4cf8bf8a43e1852524f8f5c541a2e509cd45b746b11a8ba5', 'txlist_hash': '635cf50adeff16b8d52125242aa60bc4da367b8b34f503199c2390a8f35e955e'},
    344000: {'ledger_hash': 'aeaecdf7ed6ba8ac567bf0d9337950f7d57f651166ea884a7c183d03047ea537', 'txlist_hash': '54e000b610e5b4fa39fad95a91aa00208b031b024f02dd4b1822ba2d7d2eb02a'},
    345000: {'ledger_hash': '0e6d06b77050a2094af208bf432aa271af21145e91491bdc72987cc45874a692', 'txlist_hash': '229929e82606fba0367ae9d3ed16c484acb278fe46ec8635b43f4972d745457a'},
    346000: {'ledger_hash': 'c379bc134cf74ebe51fe202fceff88b09eb82161cb3e822343394fbff5eeb3b8', 'txlist_hash': '8c841665214c921c115a1ee96fa2c61710df430a47975f32b34b61e2bfbc9c41'},
}

CONSENSUS_HASH_VERSION_TESTNET = 6
CHECKPOINTS_TESTNET = {
    config.BLOCK_FIRST_TESTNET: {'ledger_hash': '3e2cd73017159fdc874453f227e9d0dc4dabba6d10e03458f3399f1d340c4ad1', 'txlist_hash': '3e2cd73017159fdc874453f227e9d0dc4dabba6d10e03458f3399f1d340c4ad1'},
    313000: {'ledger_hash': '236757f707f89104dc3421ccc17b814f60062a4b3417131cd83f4e7458ea989f', 'txlist_hash': '9d1d0b1f8bb99e14a2603abc50ad4141263f7e9a349873cad51bdea993521e9a'},
}

class ConsensusError(Exception):
    pass

def consensus_hash(db, field, previous_consensus_hash, content):
    cursor = db.cursor()
    block_index = util.CURRENT_BLOCK_INDEX

    # Initialise previous hash on first block.
    if block_index == config.BLOCK_FIRST:
        assert not previous_consensus_hash
        previous_consensus_hash = util.dhash_string(CONSENSUS_HASH_SEED)

    # Get previous hash.
    if not previous_consensus_hash:
        try:
            previous_consensus_hash = list(cursor.execute('''SELECT * FROM blocks WHERE block_index = ?''', (block_index - 1,)))[0][field]
        except IndexError:
            previous_consensus_hash = None
        if not previous_consensus_hash:
            raise ConsensusError('Empty previous {} for block {}. Please launch a `reparse`.'.format(field, block_index))

    # Calculate current hash.
    consensus_hash_version = CONSENSUS_HASH_VERSION_TESTNET if config.TESTNET else CONSENSUS_HASH_VERSION_MAINNET
    calculated_hash = util.dhash_string(previous_consensus_hash + '{}{}'.format(consensus_hash_version, ''.join(content)))

    # Verify hash (if already in database) or save hash (if not).
    found_hash = list(cursor.execute('''SELECT * FROM blocks WHERE block_index = ?''', (block_index,)))[0][field]
    if found_hash:
        # Check against existing value.
        if calculated_hash != found_hash:
            raise ConsensusError('Inconsistent {} for block {}.'.format(field, block_index))
    else:
        # Save new hash.
        cursor.execute('''UPDATE blocks SET {} = ? WHERE block_index = ?'''.format(field), (calculated_hash, block_index))

    # Check against checkpoints.
    checkpoints = CHECKPOINTS_TESTNET if config.TESTNET else CHECKPOINTS_MAINNET
    if block_index in checkpoints and checkpoints[block_index][field] != calculated_hash:
        raise ConsensusError('Incorrect {} for block {}. got {} expected {}.'.format(field, block_index, calculated_hash, checkpoints[block_index][field]))

    return calculated_hash

class SanityError(Exception):
    pass

def asset_conservation(db):
    logger.debug('Checking for conservation of assets.')
    supplies = util.supplies(db)
    held = util.held(db)
    for asset in supplies.keys():
        asset_issued = supplies[asset]
        asset_held = held[asset] if asset in held and held[asset] != None else 0
        if asset_issued != asset_held:
            raise SanityError('{} {} issued ≠ {} {} held'.format(util.value_out(db, asset_issued, asset), asset, util.value_out(db, asset_held, asset), asset))
        logger.debug('{} has been conserved ({} {} both issued and held)'.format(asset, util.value_out(db, asset_issued, asset), asset))

class VersionError(Exception):
    pass
class VersionUpdateRequiredError(VersionError):
    pass

def check_change(protocol_change, change_name):

    # Check client version.
    passed = True
    if config.VERSION_MAJOR < protocol_change['minimum_version_major']:
        passed = False
    elif config.VERSION_MAJOR == protocol_change['minimum_version_major']:
        if config.VERSION_MINOR < protocol_change['minimum_version_minor']:
            passed = False
        elif config.VERSION_MINOR == protocol_change['minimum_version_minor']:
            if config.VERSION_REVISION < protocol_change['minimum_version_revision']:
                passed = False

    if not passed:
        explanation = 'Your version of {} is v{}, but, as of block {}, the minimum version is v{}.{}.{}. Reason: ‘{}’. Please upgrade to the latest version and restart the server.'.format(
            config.APP_NAME, config.VERSION_STRING, protocol_change['block_index'], protocol_change['minimum_version_major'], protocol_change['minimum_version_minor'],
            protocol_change['minimum_version_revision'], change_name)
        if util.CURRENT_BLOCK_INDEX >= protocol_change['block_index']:
            raise VersionUpdateRequiredError(explanation)
        else:
            warnings.warn(explanation)

def software_version():
    if config.FORCE:
        return
    logger.debug('Checking version.')

    try:
        host = 'https://counterpartyxcp.github.io/counterparty-lib/counterpartylib/protocol_changes.json'
        response = requests.get(host, headers={'cache-control': 'no-cache'})
        versions = json.loads(response.text)
    except (requests.exceptions.ConnectionError, ConnectionRefusedError, ValueError) as e:
        logger.warning('Unable to check version! ' + str(sys.exc_info()[1]))
        return

    for change_name in versions:
        protocol_change = versions[change_name]
        try:
            check_change(protocol_change, change_name)
        except VersionUpdateRequiredError as e:
            logger.error("Version Update Required", exc_info=sys.exc_info())
            sys.exit(config.EXITCODE_UPDATE_REQUIRED)

    logger.debug('Version check passed.')


class DatabaseVersionError(Exception):
    def __init__(self, message, reparse_block_index):
        super(DatabaseVersionError, self).__init__(message)
        self.reparse_block_index = reparse_block_index

def database_version(db):
    if config.FORCE:
        return
    logger.debug('Checking database version.')

    version_major, version_minor = database.version(db)
    if version_major != config.VERSION_MAJOR:
        # Rollback database if major version has changed.
        raise DatabaseVersionError('Client major version number mismatch ({} ≠ {}).'.format(version_major, config.VERSION_MAJOR), config.BLOCK_FIRST)
    elif version_minor != config.VERSION_MINOR:
        # Reparse all transactions if minor version has changed.
        raise DatabaseVersionError('Client minor version number mismatch ({} ≠ {}).'.format(version_minor, config.VERSION_MINOR), None)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
