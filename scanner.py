from ibapi.scanner import ScannerSubscription

class MarketScanner:
    def __init__(self, app):
        self.app = app

    def requestMarketScanner(self):
        subscription = ScannerSubscription()
        subscription.instrument = "STK"
        subscription.locationCode = "STK.US.MAJOR"
        subscription.scanCode = "HOT_BY_VOLUME"
        self.app.reqScannerSubscription(1, subscription, [], [
            {"tag": "priceAbove", "value": "2"},
            {"tag": "marketCapAbove", "value": "1000000"},
            {"tag": "marketCapBelow", "value": "2000000000"},
            {"tag": "averageVolumeAbove", "value": "100000"},
        ])

    def scannerData(self, reqId: int, rank: int, contractDetails, distance, benchmark, projection, legsStr):
        print(f"Scanner Data: Rank: {rank}, Contract Details: {contractDetails}")
        self.app.scanner_data.append(contractDetails)

    def scannerDataEnd(self, reqId: int):
        print("Scanner data transmission complete")
        self.app.scanner_data_event.set()
