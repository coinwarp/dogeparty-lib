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
from dogepartylib.lib import backend_server

CONSENSUS_HASH_SEED = 'We can only see a short distance ahead, but we can see plenty there that needs to be done.'

CONSENSUS_HASH_VERSION_MAINNET = 2
CHECKPOINTS_MAINNET = {
    config.BLOCK_FIRST_MAINNET: {'ledger_hash': '766ff0a9039521e3628a79fa669477ade241fc4c0ae541c3eae97f34b547b0b7', 'txlist_hash': '766ff0a9039521e3628a79fa669477ade241fc4c0ae541c3eae97f34b547b0b7'},
    336000: {'ledger_hash': '7128e9afba5261cd48ee217b6d8d563629493aa27f2a57e50aa404d4382797f2', 'txlist_hash': '83bdd2e96f468839f9cb81a48bc1d8f453c5df100e62ff32ed1b4f95e19d853e'},
    337000: {'ledger_hash': '2191046555d0fb816ddc2b264d43e894f99b629146f639471371169fc20b76f3', 'txlist_hash': 'e527fcf3d603cf5522de394795bd040363d88567fb44ef034f911301093d6440'},
    338000: {'ledger_hash': 'afffc04da367f438a9629cfeb1e33bafbb7c3932e4b8c7e598bdbebdc5e7f7f5', 'txlist_hash': '211c680ca16b9409c19cb6e4910285df7dabc0b4c14321d970a946e6d2978ee3'},
    339000: {'ledger_hash': '68f7a70c8839d10313598cb9b71ded18ff2dfe9ec0059c79789690be3ec8b273', 'txlist_hash': '433341dd661b511841573f98d4179dbb6f8a7729fc10d4702aa6b67260a75116'},
    340000: {'ledger_hash': 'ea130d42eb0934d531bb67bb389473be64e95478483b647d243fd7260a49b459', 'txlist_hash': 'da2c1f0911a9a3bd537cf35de6250870caca54bd296332f91fc7871066275071'},
    341000: {'ledger_hash': '1a9c6a60065786d36a97861bbbd8d18ca095abb4201540bc2f1d7f329639fc31', 'txlist_hash': 'fb4590a30609951295f30dbdb068ab3da56c3b78b9603ae44e240577492f298a'},
    342000: {'ledger_hash': 'fb1d9d83edf7d1ed1ddf40ac9f8f452c2819987e5c606fee46865d707281f099', 'txlist_hash': 'c20912a964e4c41f8ffd69760a81bf266a8d7d46374b3b6da914e1949a86435b'},
    343000: {'ledger_hash': 'b008a6c1bf644bc746c5491df6a6f8161a3ed84078f2b66b465f9136d0112e19', 'txlist_hash': '0f7f6ce9532038fbbc2a75415628af8e02c7156b51b85bf2a1e8f2af185f30a0'},
    344000: {'ledger_hash': 'd7f7eae91eca5f3dfd9b16a5442e9f422b0fe12129dae110faa3e0b05e2a6aaf', 'txlist_hash': 'db13a4166125c3bc106747c0700bfa147d536b6f0ac7d0192902c59903162eb4'},
    345000: {'ledger_hash': 'e90a456b8800f8346d606e7bda2a56a8bf6daf34b6a0cbe3eb3eec597431ba01', 'txlist_hash': '872a8e423b8dd4bdde1b3da172dd191a81ec71e579a418ba32a387382ef7c501'},
    346000: {'ledger_hash': 'e72e5d9100baea204dc8e2e0bf757ed74d29e965c333eb067ef8e85ec62c3847', 'txlist_hash': 'fc7e96966b8b98777785cc13d022a5985ce7bfb966bb7f599f150d19629bb442'},
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

    versions = backend_server.get_versions()
    if not versions:
        logger.warning('Unable to check version, likely due to disconnection')
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
