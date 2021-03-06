"""
Fixtures and setup / teardown functions

Tasks:
1. setup test database before starting the tests
2. delete test database after running the tests
"""

import pytest
import rethinkdb as r

from bigchaindb import Bigchain
from bigchaindb import db
from bigchaindb.exceptions import DatabaseAlreadyExists


@pytest.fixture(autouse=True)
def restore_config(request, node_config):
    from bigchaindb import config_utils
    config_utils.set_config(node_config)


@pytest.fixture(scope='module', autouse=True)
def setup_database(request, node_config):
    print('Initializing test db')
    db_name = node_config['database']['name']
    conn = db.get_conn()

    if r.db_list().contains(db_name).run(conn):
        r.db_drop(db_name).run(conn)

    try:
        db.init_database()
    except DatabaseAlreadyExists:
        print('Database already exists.')

    print('Finishing init database')

    def fin():
        print('Deleting `{}` database'.format(db_name))
        db.get_conn().repl()
        try:
            r.db_drop(db_name).run()
        except r.ReqlOpFailedError as e:
            if e.message != 'Database `{}` does not exist.'.format(db_name):
                raise
        print('Finished deleting `{}`'.format(db_name))

    request.addfinalizer(fin)


@pytest.fixture(scope='function', autouse=True)
def cleanup_tables(request, node_config):
    db_name = node_config['database']['name']

    def fin():
        db.get_conn().repl()
        try:
            r.db(db_name).table('bigchain').delete().run()
            r.db(db_name).table('backlog').delete().run()
            r.db(db_name).table('votes').delete().run()
        except r.ReqlOpFailedError as e:
            if e.message != 'Database `{}` does not exist.'.format(db_name):
                raise

    request.addfinalizer(fin)


@pytest.fixture
def inputs(user_vk):
    from bigchaindb.exceptions import GenesisBlockAlreadyExistsError
    # 1. create the genesis block
    b = Bigchain()
    try:
        b.create_genesis_block()
    except GenesisBlockAlreadyExistsError:
        pass

    # 2. create block with transactions for `USER` to spend
    for block in range(4):
        transactions = []
        for i in range(10):
            tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
            tx_signed = b.sign_transaction(tx, b.me_private)
            transactions.append(tx_signed)

        block = b.create_block(transactions)
        b.write_block(block, durability='hard')
