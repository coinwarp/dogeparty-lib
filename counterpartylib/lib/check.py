import json
import requests
import logging
logger = logging.getLogger(__name__)
import warnings
import time
import sys

from counterpartylib.lib import config
from counterpartylib.lib import util
from counterpartylib.lib import exceptions
from counterpartylib.lib import backend
from counterpartylib.lib import database

CONSENSUS_HASH_SEED = 'We can only see a short distance ahead, but we can see plenty there that needs to be done.'

CONSENSUS_HASH_VERSION_MAINNET = 2
CHECKPOINTS_MAINNET = {
    config.BLOCK_FIRST_MAINNET: {'ledger_hash': '766ff0a9039521e3628a79fa669477ade241fc4c0ae541c3eae97f34b547b0b7', 'txlist_hash': '766ff0a9039521e3628a79fa669477ade241fc4c0ae541c3eae97f34b547b0b7'},
    336000: {'ledger_hash': 'ebe9bae9e0d6ef4f7ef729ecba28b8f4f9829e2303733f1ff6ef649c9b7556c8', 'txlist_hash': 'a38eb029943f563fa8cb2a1447d23b46a5b8608a5ef06e63091526680bd969f1'},
    337000: {'ledger_hash': '4cd7586c934d8f9a839e8a010cf0023e0971db34cd138d454b60a7d0d222032f', 'txlist_hash': '20f01e01b7a7456a13b89bc49d6493a0b052ad98fb9c7f2ea5d953d6c600622f'},
    338000: {'ledger_hash': '78e947190c76bf3a5156d47e098871241b8710694f5f71f2b7d0b9db9adb9dd7', 'txlist_hash': '306204d22f4e8ee7db619d97cb151587e3dd050f27605c1d4b22a4d8877b4305'},
    339000: {'ledger_hash': '8502d024910ef6a3b15fe558e94867d80bf9d84dda1e5e6cb4b8c4b22b48facd', 'txlist_hash': '942bd83baa1762904e78be18f0ef6a7c24481a6aed28ff50ca40dbaa789d6231'},
    340000: {'ledger_hash': '188dea32a3df049a6b4f11c23ca2d48f560d0d465462d7f32d3f222828a823dc', 'txlist_hash': '4370a052f4c0c1e955ef80f671b188b9e1b72ea96858f24965721bb61426df34'},
    341000: {'ledger_hash': '34d62b8637cee900c89f2f3b33f5b31c821feab6efe58f6b4f13f1bb7bdbbdfd', 'txlist_hash': '861c0b7fa16e153ca267336958689f1ba5a6100a90f885dd0264d2be36c08216'},
    342000: {'ledger_hash': '47ad655b711d1490ed17854f3d79f676dcfa3f002a80ab72dce43112be1c259f', 'txlist_hash': '324ac513b083dc00f12c727e2942e09629628d1a24efd9dea26b1e50c4acf683'},
    343000: {'ledger_hash': '8f7bd7aa4735dd60733e869c6384b623487a2723888550c4643cb8129fc7fa0e', 'txlist_hash': 'f3f960dd2212f23f360a6129e255c2c97ea8c2fb567cc27ada75f1f2696ae49f'},
    344000: {'ledger_hash': '27e3f345c9967215c8e9ff5eaf74ed0d841ffe58404590133b1217c8b04c7e7d', 'txlist_hash': 'a18411004dd91f5dde9c4942472b8c70c89022bebfbf9320963cc48afe0166b0'},
    345000: {'ledger_hash': '288ad821e781dcf0ffe7059bc9a1ebd0352e356541c600455f2d203b2aa92ceb', 'txlist_hash': '49e0856e4289c26b34fe3fdf8b2b9d17e8a7cd1c44980ac1f9fd987ffd391f87'},
    346000: {'ledger_hash': 'a26e0896872b084297f7fad484326ca3f162398744cdea7dd965bad52688bb2f', 'txlist_hash': 'acb013bc775b45f89ad00d7f06328a23c39908acadbcc1d46497ac04c6e585b4'},
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
        raise ConsensusError('Incorrect {} for block {}.'.format(field, block_index))

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
