from flask import Flask
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
from telegram.ext import Updater, CallbackContext
from telegram_bot_ib import send_telegram_message, bot_token
from scanner import MarketScanner

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self._next_order_id = None
        self.connected_event = threading.Event()
        self.positions_event = threading.Event()
        self.positions = []
        self.prices = {}
        self.prices_event = threading.Event()
        self.pnl_event = threading.Event()
        self.pnl = 0
        self.latest_pnl = "PnL Info Not Yet Received"  # Default message
        self.what_if_order_info = None
        self.what_if_order_event = threading.Event()

    def nextValidId(self, order_id: int):
        super().nextValidId(order_id)
        self._next_order_id = order_id
        self.connected_event.set()

    def nextOrderId(self) -> int:
        return self._next_order_id

    def position(self, account: str, contract, pos: float, avg_cost: float):
        self.positions.append((contract, pos, avg_cost))

    def positionEnd(self):
        self.positions_event.set()

    def get_positions(self):
        self.positions_event.clear()
        self.positions = []
        self.reqPositions()
        self.positions_event.wait()
        return self.positions

    def tickPrice(self, reqId: int, tickType, price, attrib):
        if tickType == 4:  # Last price
            self.prices[reqId] = price
            self.prices_event.set()
    
    def pnlSingle(self, reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value):
        
        self.pnl = dailyPnL  
        self.latest_pnl = f"Daily PnL: {dailyPnL}, Unrealized PnL: {unrealizedPnL}, Realized PnL: {realizedPnL}"
        self.pnl_event.set()  # Signal that new PnL info is available

    def get_pnl(self):
        return self.latest_pnl

    def openOrder(self, orderId, contract, order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        if order.whatIf:
            self.what_if_order_info = {
                "initMarginChange": float(orderState.initMarginChange),
                "equityWithLoanBefore": float(orderState.equityWithLoanBefore)
            }
            self.what_if_order_event.set()

app = IBApp()
app.connect("127.0.0.1", 4001, clientId=1)

scanner = MarketScanner(app)  # Create a MarketScanner instance

thread = threading.Thread(target=app.run, daemon=True)
thread.start()

app.connected_event.wait()

# Start market scanner
scanner.requestMarketScanner()

flask_app = Flask(__name__)

from order_module_ib import process_alert
process_alert(flask_app, app)

def send_pnl_info(context: CallbackContext):
    pnl_info = app.get_pnl()  
    send_telegram_message(pnl_info)

# Telegram Bot Setup
updater = Updater(token=bot_token, use_context=True)
job_queue = updater.job_queue

# Add job to send PnL info every hour
job_queue.run_repeating(send_pnl_info, interval=3600, first=0)

updater.start_polling()
updater.idle()

if __name__ == "__main__":
    flask_app.run(host='0.0.0.0', port=80)
