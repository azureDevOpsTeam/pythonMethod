from fastapi import FastAPI, HTTPException
from mnemonic import Mnemonic
import requests
from hashlib import sha256
from tronpy.keys import PrivateKey
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_string_canonize
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from dotenv import load_dotenv
import os

load_dotenv()


app = FastAPI()

@app.get("/generate-wallet")
async def generate_wallet():
    mnemonic = Mnemonic("english").generate(strength=128)
    print("Mnemonic Phrase:", mnemonic)
    seed = Mnemonic("english").to_seed(mnemonic)
    private_key = PrivateKey.from_seed(seed[:32])  # Tron uses the first 32 bytes of the seed

    public_key = private_key.public_key
    address = Tron().address.from_public_key(public_key)
    return {
        "seed" : seed,
        "private_key" : private_key,
        "public_key" : public_key,
        "address" : address
    }

@app.get("/create-transaction")
async def create_transaction(tronKey: str, ownerAddress: str, toAddress: str, privateKey: str, amount: float):
    try:
        if not (ownerAddress.startswith("T") and len(ownerAddress) == 34):
            return {"error": "Invalid owner address"}
        if not (toAddress.startswith("T") and len(toAddress) == 34):
            return {"error": "Invalid recipient address"}
        if len(privateKey) != 64:
            return {"error": "Invalid private key"}
        if amount <= 0:
            return {"error": "Amount must be greater than zero"}

        amount_sun = int(amount * 1e6)
        provider = HTTPProvider(api_key=tronKey)
        client = Tron(provider=provider)

        txn_builder = client.trx.transfer(ownerAddress, toAddress, amount_sun)
        txn = txn_builder.build()
        private_key = PrivateKey(bytes.fromhex(privateKey))
        signed_txn = txn.sign(private_key)
        
        result = signed_txn.broadcast()
        if result.get("result", False):
            return {
                "success": "Transaction broadcasted successfully!",
                "txid": result.get("txid")
            }
        else:
            return {
                "error": "Transaction failed to broadcast",
                "details": result
            }
    except ValueError as e:
        return {"error": "Invalid input values", "details": str(e)}
    except Exception as e:
        return {"error": "An unexpected error occurred", "details": str(e)}

@app.get("/transfer-usdt")
async def transfer_usdt(tronKey: str, ownerAddress: str, toAddress: str, privateKey: str, amount: float):
    try:
        usdt_contract_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        if not (ownerAddress.startswith("T") and len(ownerAddress) == 34):
            return {"error": "Invalid owner address"}
        if not (toAddress.startswith("T") and len(toAddress) == 34):
            return {"error": "Invalid recipient address"}
        if len(privateKey) != 64:
            return {"error": "Invalid private key"}
        if amount <= 0:
            return {"error": "Amount must be greater than zero"}

        amount_sun = int(amount * 1e6)
        provider = HTTPProvider(api_key=tronKey)
        client = Tron(provider=provider)

        contract = client.get_contract(usdt_contract_address)
        txn_builder = contract.functions.transfer(toAddress, amount_sun)

        txn = txn_builder.with_owner(ownerAddress).build()
        private_key = PrivateKey(bytes.fromhex(privateKey))
        signed_txn = txn.sign(private_key)

        result = signed_txn.broadcast()

        if result.get("result", False):
            return {
                "success": "USDT transferred successfully!",
                "txid": result.get("txid")
            }
        else:
            return {
                "error": "Transaction failed to broadcast",
                "details": result
            }
    except ValueError as e:
        return {"error": "Invalid input values", "details": str(e)}
    except Exception as e:
        return {"error": "An unexpected error occurred", "details": str(e)}

@app.get("/get-balance")
async def get_balance():
    tron_api_key = os.getenv("tronKey")
    # tron_api_key = "18707539-0b5e-4818-96c6-9e68c08988a7"
    address = "TUJN945qzsEhQxepiGMpfTwZDRBYRfi7xT"  # Example address
    provider = HTTPProvider(api_key=tron_api_key)
    client = Tron(provider=provider)
    # Address to check the balance for

    try:
        # Get account data for the address
        account = client.get_account(address)

        # Account data includes balance in Sun
        balance_sun = account.get('balance', 0)

        # Convert the balance from Sun to TRX
        balance_trx = balance_sun / 1e6

        return {"address": address, "balance_trx": balance_trx, "balance_sun": balance_sun}
    
    except Exception as e:
        return {"error": "Error while fetching balance", "details": str(e)}

@app.get("/get_bandwidth_price")
def get_bandwidth_price():
    try:
        url = "https://api.trongrid.io/wallet/getchainparameters"

        headers = {
            "TRON-PRO-API-KEY": "18707539-0b5e-4818-96c6-9e68c08988a7",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status() 

        data = response.json()
        chain_parameters = data.get('chainParameter', [])
        
        bandwidth_price_param = next((param for param in chain_parameters if param.get('key') == 'getBandwidthPrice'), None)
        
        if not bandwidth_price_param:
            return {"error": "Bandwidth price parameter not found in response"}
        
        bandwidth_price_trx = bandwidth_price_param['value'] / 1_000_000

        return {"bandwidth_price_trx": bandwidth_price_trx}

    except requests.RequestException as e:
        return {"error": "Error while fetching bandwidth price", "details": str(e)}
    except Exception as e:
        return {"error": "Unexpected error occurred", "details": str(e)}


@app.get("/get_trc20_fee")
def get_trc20_fee():
    try:
        contract_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        owner_address = "TUJN945qzsEhQxepiGMpfTwZDRBYRfi7xT"
        to_address = "TKsApTpoUsMTYBTdSH5wjBhy1eG5RpVrGm"
        amount_sun = int(1 * 1e6)

        # تخمین کارمزد تراکنش
        url = "https://api.trongrid.io/wallet/triggerconstantcontract"
        headers = {
            "TRON-PRO-API-KEY": "18707539-0b5e-4818-96c6-9e68c08988a7",
            "Content-Type": "application/json"
        }
        
        # تنظیم درخواست برای فراخوانی تابع انتقال توکن TRC20
        payload = {
            "contract_address": contract_address,
            "function_selector": "transfer(address,uint256)",
            "parameter": f"{to_address[2:].zfill(64)}{hex(amount_sun)[2:].zfill(64)}",
            "owner_address": owner_address
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # بررسی مصرف Bandwidth و Energy
        bandwidth_used = data.get("bandwidth_used", 0)
        energy_used = data.get("energy_used", 0)

        # دریافت قیمت پهنای باند و انرژی
        #chain_params_url = f"{TRON_API_URL}/wallet/getchainparameters"
        chain_params_url = "https://api.trongrid.io/wallet/getchainparameters"
        chain_response = requests.get(chain_params_url, headers=headers)
        chain_response.raise_for_status()
        chain_data = chain_response.json()

        # استخراج قیمت‌ها
        bandwidth_price = next(
            param["value"] for param in chain_data["chainParameter"] if param["key"] == "getBandwidthPrice"
        )
        energy_price = next(
            param["value"] for param in chain_data["chainParameter"] if param["key"] == "getEnergyFee"
        )

        # محاسبه هزینه کل به TRX
        bandwidth_cost_trx = (bandwidth_used * bandwidth_price) / 1_000_000
        energy_cost_trx = (energy_used * energy_price) / 1_000_000
        total_cost_trx = bandwidth_cost_trx + energy_cost_trx

        # خروجی ساده برای کاربر
        return {
            "message": "Total fee for transferring tokens",
            "total_fee_in_trx": round(total_cost_trx, 6)  # گرد کردن به 6 رقم اعشار
        }

    except requests.RequestException as e:
        return {"error": "Error while fetching fee details", "details": str(e)}
    except Exception as e:
        return {"error": "Unexpected error occurred", "details": str(e)}

import requests
import logging
import traceback
logging.basicConfig(level=logging.DEBUG)

@app.get("/get_trc20_contract_fee")
def get_trc20_contract_fee():
    try:
        contract_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        owner_address = "TUJN945qzsEhQxepiGMpfTwZDRBYRfi7xT"
        to_address = "TKsApTpoUsMTYBTdSH5wjBhy1eG5RpVrGm"
        amount_sun = int(1 * 1e6)

        url = "https://api.trongrid.io/wallet/triggerconstantcontract"
        headers = {
            "TRON-PRO-API-KEY": "18707539-0b5e-4818-96c6-9e68c08988a7",
            "Content-Type": "application/json"
        }
        
        payload = {
            "contract_address": contract_address,
            "function_selector": "transfer(address,uint256)",
            "parameter": f"{to_address[2:].zfill(64)}{hex(amount_sun)[2:].zfill(64)}",
            "owner_address": owner_address
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        logging.debug(f"Response from triggerconstantcontract: {data}")

        bandwidth_used = data.get("bandwidth_used", 0)
        energy_used = data.get("energy_used", 0)

        # Chain parameters request
        chain_params_url = "https://api.trongrid.io/wallet/getchainparameters"
        chain_response = requests.get(chain_params_url, headers=headers)
        chain_response.raise_for_status()
        chain_data = chain_response.json()

        logging.debug(f"Response from getchainparameters: {chain_data}")

        bandwidth_price = next(
            param["value"] for param in chain_data["chainParameter"] if param["key"] == "getBandwidthPrice"
        )
        energy_price = next(
            param["value"] for param in chain_data["chainParameter"] if param["key"] == "getEnergyFee"
        )

        bandwidth_cost_trx = (bandwidth_used * bandwidth_price) / 1_000_000
        energy_cost_trx = (energy_used * energy_price) / 1_000_000
        total_cost_trx = bandwidth_cost_trx + energy_cost_trx

        return {
            "message": "Total fee for transferring tokens",
            "total_fee_in_trx": round(total_cost_trx, 6)
        }

    except requests.RequestException as e:
        logging.error(f"Request exception occurred: {e}")
        return {"error": "Error while fetching fee details", "details": str(e)}
    except Exception as e:
        logging.error(f"Unexpected exception: {str(e)}\n{traceback.format_exc()}")
        return {"error": "Unexpected error occurred", "details": str(e)}
