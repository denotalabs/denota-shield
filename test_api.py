import json
import pytest
from app import app  # Replace with the name of your API file.
import dotenv

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


def test_register_onramp(client):
    rv = client.post('/register', json=test_data)
    assert rv.status_code in [200, 201, 409]


def test_onramp_signin(client):
    rv = client.post('/signin', json={
        "email": test_data["email"],
        "password": test_data["password"]
    })
    token = rv.data.decode("utf-8")
    test_data["testToken"] = token
    
    assert rv.status_code == 200 or rv.status_code == 201


def test_add_nota(client):
    rv = client.post('/nota', json={
        "paymentAmount": test_data["paymentAmount"],
        "riskScore": test_data["riskScore"]
    }, headers={'Authorization': test_data["testToken"]})

    nota_id = json.loads(rv.data.decode("utf-8"))["notaId"]
    test_data["notaId"] = nota_id

    assert rv.status_code == 201


def test_initiate_recovery(client):
    rv = client.post('/recovery', json={
        "notaId": test_data["notaId"],
        "proofOfChargeback": test_data["proofOfChargeback"]
    }, headers={'Authorization': test_data["testToken"]})
    assert rv.status_code == 200


def test_get_recovery(client):
    rv = client.get(f'/recovery/{test_data["notaId"]}', headers={'Authorization': test_data["testToken"]})
    assert rv.status_code == 200
