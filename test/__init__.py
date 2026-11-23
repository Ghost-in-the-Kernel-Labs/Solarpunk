"""The tests' one setting: every test hashes passwords at a low scrypt cost (13.19, SP-054). Test discovery imports this
package before any test module, so the demo store's build and every account a test makes pay 2 ** 4, not the product's
16384 (about 30 ms a hash). The product reads nothing from the environment; a stored line carries its own parameters, so
a line at either cost verifies, and test_password_cost holds the product's own values."""
from solarpunk.accounts import passwords

TEST_SCRYPT_COST = 2 ** 4
passwords.SCRYPT_COST = TEST_SCRYPT_COST
