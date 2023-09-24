import pytest
from app import app  # Replace with the name of your API file.
import dotenv

env_path = ".env"
testEmail = dotenv.get_key(dotenv_path=env_path, key_to_get='TEST_EMAIL')
testPassword = dotenv.get_key(dotenv_path=env_path, key_to_get="TEST_PASSWORD")
testToken = dotenv.get_key(dotenv_path=env_path, key_to_get="TEST_TOKEN")

# The data used for testing the endpoints.
test_data = {
    "email": testEmail,
    "password": testPassword,
    "onrampName": "test",
    "coverageTier": "silver",
    "historicalChargebackData": "",
    "paymentAmount": 200,
    "paymentTime": "2023-09-24T14:39:22.752Z",
    "withdrawalTime": "2023-09-25T14:39:22.752Z",
    "notaId": 1,
    "proofOfChargeback": "testproof"
}

# bearer_token = None # TODO how to pass this around to simulate sessions

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_register_onramp(client):
    rv = client.post('/register', json=test_data)
    assert b"Registration successful" in rv.data


def test_onramp_signin(client):
    rv = client.post('/signin', json={
        "email": test_data["email"],
        "password": test_data["password"]
    })
    assert rv.status_code == 200 or rv.status_code == 201


def test_add_nota(client):
    rv = client.post('/nota', json={
        "paymentAmount": test_data["paymentAmount"],
        "paymentTime": test_data["paymentTime"],
        "withdrawalTime": test_data["withdrawalTime"]
    }, headers={'Authorization': testToken})
    assert rv.status_code == 201


def test_initiate_recovery(client):
    rv = client.post('/recovery', json={
        "notaId": test_data["notaId"],
        "proofOfChargeback": test_data["proofOfChargeback"]
    }, headers={'Authorization': testToken})
    assert rv.status_code == 200


def test_get_recovery(client):
    rv = client.get(f'/recovery/{test_data["notaId"]}', headers={'Authorization': testToken})
    assert rv.status_code == 200
