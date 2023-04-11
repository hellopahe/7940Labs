from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

# Connect to MySQL database
mydb = mysql.connector.connect(
  host="51.120.244.80",
  user="root",
  password="cptbtptp",
  database="database_project"
)

## added in 11q April, Get orders by user and shop.
@app.route('/orders/<int:customer_id>', methods=['GET'])
def get_users_orders(customer_id):  # get orders of some customer.
    mycursor = mydb.cursor()
    sql = "SELECT * FROM OrderTable WHERE customer_id = %s"
    val = (customer_id,)
    mycursor.execute(sql, val)
    items = mycursor.fetchall()
    return jsonify(items)



@app.route('/rating/<int:shop_id>', methods=['GET'])
def get_shop_rating(shop_id): # get rating of a shop, calculated by the number of canceled orders.
    mycursor = mydb.cursor()

    sql = "SELECT * FROM OrderTable WHERE order_id IN ( SELECT order_id FROM OrderItem WHERE shop_id = %s);"
    val = (shop_id, )
    mycursor.execute(sql, val)
    shop_orders = mycursor.fetchall()

    pending_orders = 0
    canceled_orders = 0

    for ele in shop_orders:
        if ele[4] == "pending":
            pending_orders += 1
        else:
            canceled_orders += 1

    return jsonify(5 * (pending_orders / (pending_orders + canceled_orders)))


@app.route('/orders_number', methods=['GET'])
def get_order_number():  # get the total number of orders.
    mycursor = mydb.cursor()
    mycursor.execute('SELECT count(*) FROM OrderTable where 1;')
    total_order_number = mycursor.fetchall()
    return jsonify(total_order_number)

# Customer account management
@app.route('/customers', methods=['POST'])
def add_customers(): # add new customer
    tele = request.json['telephone']
    addr = request.json['address']
    mycursor = mydb.cursor()
    sql = "INSERT INTO Customer (telephone, address) VALUES (%s, %s)"
    val = (tele, addr)
    mycursor.execute(sql, val)
    mydb.commit()
    return 'success'

@app.route('/customers', methods=['GET'])
def get_customers(): # get all customers
    mycursor = mydb.cursor()
    mycursor.execute('SELECT * FROM Customer')
    customers = mycursor.fetchall()
    return jsonify(customers)

# Shop account management
@app.route('/shops', methods=['GET'])
def get_shops():  # get all shops
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM Shop")
    shops = mycursor.fetchall()
    return jsonify(shops)

@app.route('/shops', methods=['POST'])
def add_shop():  # add shop
    shop_name = request.json['shop_name']
    rating = request.json['rating']
    location = request.json['location']
    print(request.json)
    mycursor = mydb.cursor()
    sql = "INSERT INTO Shop (shop_name, rating, location) VALUES (%s, %s, %s)"
    val = (shop_name, rating, location)
    mycursor.execute(sql, val)
    mydb.commit()
    return "Shop added successfully"

# Item management by shop_id
@app.route('/shops/<int:shop_id>/items', methods=['GET'])
def get_items(shop_id):  # get all items
    mycursor = mydb.cursor()
    sql = "SELECT * FROM Item WHERE shop_id = %s"
    val = (shop_id,)
    mycursor.execute(sql, val)
    items = mycursor.fetchall()
    return jsonify(items)

@app.route('/shops/<int:shop_id>/items', methods=['POST'])
def add_item(shop_id): # add single item
    item_name = request.json['item_name']
    price = request.json['price']
    keyword1 = request.json.get('keyword1', None)
    keyword2 = request.json.get('keyword2', None)
    keyword3 = request.json.get('keyword3', None)
    mycursor = mydb.cursor()
    sql = "INSERT INTO Item (shop_id, item_name, price, keyword1, keyword2, keyword3) VALUES (%s, %s, %s, %s, %s, %s)"
    val = (shop_id, item_name, price, keyword1, keyword2, keyword3)
    mycursor.execute(sql, val)
    mydb.commit()
    return "Item added successfully"

# Item purchase by [customer_id, shop_id, item_id, quantity, price]
@app.route('/purchase', methods=['POST'])
def purchase_item():
    customer_id = request.json['customer_id']
    shop_id = request.json['shop_id']
    item_id = request.json['item_id']
    quantity = request.json['quantity']
    price = request.json['price']
    mycursor = mydb.cursor()
    sql = "INSERT INTO OrderTable (customer_id, bill_amount, order_date) VALUES (%s, %s, NOW())"
    val = (customer_id, price, )
    mycursor.execute(sql, val)

    order_id = mycursor.lastrowid
    sql = "INSERT INTO OrderItem (order_id, shop_id, item_id, quantity) VALUES (%s, %s, %s, %s)"
    val = (order_id, shop_id, item_id, quantity)
    mycursor.execute(sql, val)
    mydb.commit()
    return "Item purchased successfully"

# place order,
# [customer_id, items: [[item_id, shop_id, item_name, price, keyword1, keyword2, keyword3, quantity], []...]]
@app.route('/orders', methods=['POST'])
def place_order():
    customer_id = request.json['customer_id']
    items = request.json['items']

    total_price = 0
    for item in items:
        total_price += item[3]

    mycursor = mydb.cursor()
    mycursor.execute("INSERT INTO OrderTable (customer_id, bill_amount, order_date) VALUES (%s, %s, NOW())",
                     (customer_id, total_price, ))
    order_id = mycursor.lastrowid

    for item in items:
        shop_id = item[1]
        item_id = item[0]
        quantity = item[7]
        mycursor.execute("INSERT INTO OrderItem (order_id, shop_id, item_id, quantity) VALUES (%s, %s, %s, %s)",
                         (order_id, shop_id, item_id, quantity))

    mydb.commit()
    return "Order placed successfully"

@app.route('/orders', methods=['GET'])
def get_order(): # get all orders.
    mycursor = mydb.cursor()
    mycursor.execute('SELECT * FROM OrderTable')
    customers = mycursor.fetchall()
    return jsonify(customers)

# search
@app.route('/items/search/string:keyword', methods=['GET'])
def search_items(keyword):
    mycursor = mydb.cursor()  # get items including some keywords defined in Keyword1 - keyword3.
    sql = "SELECT * FROM Item WHERE item_name LIKE %s OR keyword1 LIKE %s OR keyword2 LIKE %s OR keyword3 LIKE %s"
    val = (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if result:
        return jsonify(result)
    else:
        return "No item found matching the search keyword"


@app.route('/orders/<int:order_id>/cancel', methods=['PUT'])
def cancel_order(order_id): # by changing status, we cancel orders.
    mycursor = mydb.cursor()
    sql = "SELECT * FROM OrderItem WHERE order_id = %s"
    val = (order_id,)
    mycursor.execute(sql, val)
    order_items = mycursor.fetchall()

    sql = "SELECT * FROM OrderTable WHERE order_id = %s"
    val = (order_id,)
    mycursor.execute(sql, val)
    order_entries = mycursor.fetchall()

    if order_entries or order_items:
        # try:
        #     sql = "DELETE FROM OrderItem WHERE order_id = %s"
        #     val = (order_id,)
        #     mycursor.execute(sql, val)
        # except:
        #     pass

        try:
            sql = "UPDATE OrderTable SET status='canceled' WHERE order_id=%s;"
            val = (order_id,)
            mycursor.execute(sql, val)
        except:
            pass

        mydb.commit()
        return "Order cancelled successfully"
    else:
        return "Order not found"



if __name__ == '__main__':
    app.run()
