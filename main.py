import APIS

api = APIS.APIs()

api.create_account("1234567890", "John Doe", "123 Main St, City, Country")

api.record_consumption("ACC_1", datetime.now(), 100)
