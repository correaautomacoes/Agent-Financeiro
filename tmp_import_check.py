import db_helpers

reports = db_helpers.get_partner_reports()
print(reports[:1])
