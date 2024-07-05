from supervisely.app.widgets import Card, CustomModelsSelector, Select, Table

# test_select = Select([Select.Item("Car")])
# widget_html = test_select.to_html()
# print(widget_html)
widget_html = "<select><option value='Car'>Car</option></select>"

table_columns = ["Name", "Color", "Shape", "Destination Class"]
table_rows = [["Car", "#ff0000", "Rectangle", widget_html]]


merge_classes_table = Table()
merge_classes_table.read_json({"columns": table_columns, "data": table_rows})
card = Card(
    "2️⃣ Merge classes",
    "Select the destination class for each class you want to merge.",
    content=merge_classes_table,
)
