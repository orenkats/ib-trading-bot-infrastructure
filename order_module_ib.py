from flask import request
from ibapi.contract import Contract
from ibapi.order import Order
from telegram_bot_ib import send_telegram_message


def process_alert(flask_app, app):
    @flask_app.route('/', methods=['POST'])
    def process():
        data = request.get_json()
        print("Received data:", data)

        params = {
            'symbol': data.get('symbol', ''),
            'side': data.get('side', '').upper(),
            'type': data.get('type', 'MKT').upper(),
            'quantity': int(data.get('quantity', 0)),
            'price': float(data.get('price', 0)),
            'typeOfAction': data.get('action', '').upper(),
        }

        # Fetch PnL data
        pnl_info = app.get_pnl()

        # Construct and send Telegram message
        msg = create_telegram_message(params, pnl_info)
        send_telegram_message(msg)

        # Perform order logic
        order_response = perform_order_logic(app, params)

        if order_response:
            return {"code": "success", "message": "order executed"}
        else:
            return {"code": "error", "message": "order failed"}
    return process

def perform_order_logic(app, params):
    contract = Contract()
    contract.symbol = params['symbol']
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"

    # Create and place a what-if order
    what_if_order = create_order(params, whatIf=True)
    app.placeOrder(app.nextOrderId(), contract, what_if_order)
    app.what_if_order_event.wait()
    app.what_if_order_event.clear()

    # Increment the next order ID
    app.nextValidId(app.nextOrderId() + 1)

    margin_impact = app.what_if_order_info
    if margin_impact and margin_impact.get('initMarginChange') is not None:
        equity_with_loan_before = margin_impact['equityWithLoanBefore']
        init_margin_change = margin_impact['initMarginChange']

        if init_margin_change > equity_with_loan_before:
            params['quantity'] = int(equity_with_loan_before / (init_margin_change / what_if_order.totalQuantity))

    # Create and place the actual order
    actual_order = create_order(params, whatIf=False)
    app.placeOrder(app.nextOrderId(), contract, actual_order)
    app.nextValidId(app.nextOrderId() + 1)  # Increment the next order ID again

    return True

def create_order(params, whatIf=False):
    order = Order()
    order.action = "BUY" if params['side'] == "BUY" else "SELL"
    order.totalQuantity = params['quantity']
    order.orderType = params['type']

    if params['type'] == "LMT":
        order.lmtPrice = params['price']
    elif params['type'] == "MKT":
        order.lmtPrice = 0  

    order.whatIf = whatIf
    order.account = 'U6119229'
    order.eTradeOnly = ''  
    order.firmQuoteOnly = ''
    return order

def create_telegram_message(params, realized_pnl):
    msg = "*************************\n"
    msg += f"Symbol: {params['symbol']}\n"
    msg += f"Side: {params['side']}\n"
    msg += f"Order Type: {params['type']}\n"
    msg += f"Quantity: {params['quantity']}\n"
    msg += f"Price: {params['price']}\n"
    msg += f"Action: {params['typeOfAction']}\n"
    msg += f"Realized PnL: {realized_pnl}\n"
    msg += "*************************\n"
    return msg

def get_price(app, symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"

    reqId = app.nextOrderId() + 1
    app.reqMktData(reqId, contract, "", False, False, [])

    received = app.prices_event.wait(timeout=5)
    if received:
        return app.prices[reqId]
    else:
        print("Price not received within the timeout period")
        return None
