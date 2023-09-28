import json

import dotenv
import pytest

from app import app  # Replace with the name of your API file.

env_path = ".env"
testEmail = dotenv.get_key(dotenv_path=env_path, key_to_get='TEST_EMAIL')
testPassword = dotenv.get_key(dotenv_path=env_path, key_to_get="TEST_PASSWORD")

# The data used for testing the endpoints.
test_data = {
    "email": testEmail,
    "password": testPassword,
    "testToken": "",
    "onrampName": "test",
    "coverageTier": "silver",
    "historicalChargebackData": "",
    "paymentAmount": 200,
    "riskScore": 100,
    "notaId": 0,
    "proofOfChargeback": {}
}


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_register_onramp(client):  # TODO handle rate limiting
    rv = client.post('/register', json=test_data, timeout=5)
    data = json.loads(rv.data.decode("utf-8"))
    address = data["address"]
    assert rv.status_code == 200
    assert address is not None


def test_onramp_signin(client):
    rv = client.post('/signin', json={
        "email": test_data["email"],
        "password": test_data["password"]
    }, timeout=5)
    token = rv.data.decode("utf-8")
    test_data["testToken"] = token

    assert rv.status_code == 200
    assert token is not None


def test_add_nota(client):
    rv = client.post('/nota', json={
        "paymentAmount": test_data["paymentAmount"],
        "riskScore": test_data["riskScore"]
    }, headers={'Authorization': test_data["testToken"]}, timeout=60)

    data = json.loads(rv.data.decode("utf-8"))
    nota_id = data["notaId"]
    onchain_id = data["onchainId"]
    test_data["notaId"] = nota_id

    assert rv.status_code == 200
    assert onchain_id is not None


def test_initiate_recovery(client):
    rv = client.post('/recovery', json={
        "notaId": test_data["notaId"],
        "proofOfChargeback": test_data["proofOfChargeback"]
    }, headers={'Authorization': test_data["testToken"]}, timeout=60)

    data = json.loads(rv.data.decode("utf-8"))
    hash = data["hash"]

    assert rv.status_code == 200
    assert hash is not None


def test_get_recovery(client):
    rv = client.get(f'/recovery/{test_data["notaId"]}',
                    headers={'Authorization': test_data["testToken"]})
    assert rv.status_code == 200
