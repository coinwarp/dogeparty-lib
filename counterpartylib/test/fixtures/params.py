"""
This is a collection of default transaction data used to test various components.
"""

UNIT = 100000000

"""This structure is used throughout the test suite to populate transactions with standardized and tested data."""
DEFAULT_PARAMS = {
    'addresses': [
        ['niVVidMwAXNtBsh8cPVXPssaHp1PKtZR6F', 'cnKDs9myJWNePfXqvSdjTQAkNNPJon74qrKAm1W2XGqkgWo1Wh3x', '030a61fc8bb05fb3fbedb6d7083f6cb8f39c12ddae6732a04df1f65351865752bb'],
        ['nhKbsrhki5U9WUKyCwqqhqZN5CwzWmXk65', 'ckau3NP8vKsqDiyySyT2ZagoaTPFRXW3yRZTRyL9ydXdmXGVLxc6', '034309e2253f69ba58f2bf334c3b9e9932baa47f36658a5a43611ff973d24fce5b'],
        ['nUtoWndFgmzPquS2iJAFUPEtVhRX7jfobH', 'cfgXNw1ChWVB3hsf7ky1MALDKGYGcRjTqBRZyASUQX1bnmbykLNV', '022d0102ab74698b3dd0c17f4bc1f4c7bf042a93aebe74894458ff91c3b5a293bc'],
        ['nW8dXfYakP7aSyPuzEcAdFyrjFXimPkvct', 'cgmvXApSFjjnAPkxNZ5wykzsFGxFjjimvGJNPtL9MscWmmSAg6yr', '038d8b64c7880994f04127c2a2a790c41f587ede08646a22471f474c5e544bc8fc']
    ],
    'quantity': UNIT,
    'small': round(UNIT / 2),
    'expiration': 10,
    'fee_required': 900000,
    'fee_provided': 1000000,
    'fee_multiplier': .05,
    'unspendable': 'ndogepartyxxxxxxxxxxxxxxxxxxwpsZCH',
    'burn_start': 124678,
    'burn_end':  26280000,
    'burn_quantity': int(.62 * UNIT),
    'default_block': 124678 + 501   # Should be called `block_index`.
}
DEFAULT_PARAMS['privkey'] = {addr: priv for (addr, priv, pub) in DEFAULT_PARAMS['addresses']}
DEFAULT_PARAMS['pubkey'] = {addr: pub for (addr, priv, pub) in DEFAULT_PARAMS['addresses']}
ADDR = [a[0] for a in DEFAULT_PARAMS['addresses']]
DP = DEFAULT_PARAMS
MULTISIGADDR = [
    '1_{}_{}_2'.format(ADDR[0], ADDR[1]),
    '1_{}_{}_2'.format(ADDR[2], ADDR[1]),
    '1_{}_{}_2'.format(ADDR[0], ADDR[2]),

    '2_{}_{}_2'.format(ADDR[0], ADDR[1]),
    '2_{}_{}_2'.format(ADDR[2], ADDR[1]),

    '1_{}_{}_{}_3'.format(ADDR[0], ADDR[2], ADDR[1]),
    '1_{}_{}_{}_3'.format(ADDR[0], ADDR[2], ADDR[3]),

    '2_{}_{}_{}_3'.format(ADDR[0], ADDR[2], ADDR[1]),
    '2_{}_{}_{}_3'.format(ADDR[0], ADDR[2], ADDR[3]),

    '3_{}_{}_{}_3'.format(ADDR[0], ADDR[2], ADDR[1]),
    '3_{}_{}_{}_3'.format(ADDR[0], ADDR[2], ADDR[3])
]
