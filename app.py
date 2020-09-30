from flask import Flask 
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime, timedelta
from faker import Faker 

import random

fake = Faker()

# Setup the application
app = Flask(__name__) # instantiate the app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3' # SQLite database connection string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # stops warnings that pop up when making changes to database
db = SQLAlchemy(app) # instantiate SQLAlchemy object. If using an app_factory then use: db.init_app(app)

# Models for database
class Customer(db.Model): # class Customer that inherits from db.Model creates a table in the database
    id = db.Column(db.Integer, primary_key=True) # class 'column' attribute (column in database), integer type, and the primary key.
    first_name = db.Column(db.String(50), nullable=False) # String up to 50 chars type, cannot be null (must have a first name)
    last_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    postcode = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False, unique=True) # email must be a unique value in the table (no duplicate email usage)

    orders = db.relationship('Order', backref='customer') # abstraction of a relationship between customers and orders. The backref indicates only one customer per order (one to many).

order_product = db.Table('order_product', # assocciation table between orders and products: two columns, each foreign keys.
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)

class Order(db.Model): # class Order that inherits from db.Model creates a table in the database
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # datetime.utcnow sets the value to datetime at point of order (UTC)
    shipped_date = db.Column(db.DateTime)
    delivered_date = db.Column(db.DateTime)
    coupon_code = db.Column(db.String(50))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False) # foreign key (represents 'id' in the customer table)

    products = db.relationship('Product', secondary=order_product) # relationship between orders and products, uses the order_product table created earlier.

class Product(db.Model): # class Product that inherits from db.Model creates a table in the database
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(50), nullable=False, unique=True) 
    price = db.Column(db.Integer, nullable=False)

def add_customers():
    for _ in range(100): # create 100 'fake' customers using the Faker library
        customer = Customer(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            address=fake.street_address(),
            city=fake.city(),
            postcode=fake.postcode(),
            email=fake.email()
        )
        db.session.add(customer)
    db.session.commit()

def add_orders():
    customers = Customer.query.all()

    for _ in range(1000): # create 1000 'fake' orders related to random customers
        #choose a random customer
        customer = random.choice(customers)

        ordered_date = fake.date_time_this_year()
        shipped_date = random.choices([None, fake.date_time_between(start_date=ordered_date)], [10, 90])[0]

        #choose either random None or random date for delivered and shipped
        delivered_date = None
        if shipped_date:
            delivered_date = random.choices([None, fake.date_time_between(start_date=shipped_date)], [50, 50])[0]

        #choose either random None or one of three coupon codes
        coupon_code = random.choices([None, '50OFF', 'FREESHIPPING', 'BUYONEGETONE'], [80, 5, 5, 5])[0]

        order = Order(
            customer_id=customer.id,
            order_date=ordered_date,
            shipped_date=shipped_date,
            delivered_date=delivered_date,
            coupon_code=coupon_code
        )

        db.session.add(order)
    db.session.commit()

def add_products():
    for _ in range(10): # create 10 fake products
        product = Product(
            name=fake.color_name(),
            price=random.randint(10,100)
        )
        db.session.add(product)
    db.session.commit()
    
def add_order_products(): # once orders and products created, add products to orders
    orders = Order.query.all()
    products = Product.query.all()

    for order in orders:
        #select random k
        k = random.randint(1, 3)
        # select random products
        purchased_products = random.sample(products, k)
        order.products.extend(purchased_products)
        
    db.session.commit()

def create_random_data(): # function that runs through each function for adding data to db
    db.create_all()
    add_customers()
    add_orders()
    add_products()
    add_order_products()

def get_orders_by(customer_id=1): # get all the orders for customer '1'
    print('Get Orders by Customer')
    customer_orders = Order.query.filter_by(customer_id=customer_id).all()
    for order in customer_orders:
        print(order.order_date)

def get_pending_orders(): # get all the orders without a shipping date / shipping date = None, ordered by the order date descening. Notice use of 'filter' rather than 'filter_by' requires the Model.columnname format.
    print('Pending Orders')
    pending_orders = Order.query.filter(Order.shipped_date.is_(None)).order_by(Order.order_date.desc()).all()
    for order in pending_orders:
        print(order.order_date)

def how_many_customers(): # counts number of entries in Customer table
    print('How many customers?')
    print(Customer.query.count())

def orders_with_code():  # orders with couponcode that is not None (with a coupon code), and second filter 'not FREESHIPPING'
    print('Orders with coupon code')
    orders = Order.query.filter(Order.coupon_code.isnot(None)).filter(Order.coupon_code != 'FREESHIPPING').all()
    for order in orders:
        print(order.coupon_code)

def revenue_in_last_x_days(x_days=30): # needs information from both the order table (the orders and order dates) and the product table (prices)
    print('Revenue past x days')
    print(db.session.query(db.func.sum(Product.price)).join(order_product).join(Order) # this query sums the product prices where the product table joins the order table via the order_product assocciational table
        .filter(Order.order_date > (datetime.now() - timedelta(days=x_days))).scalar() # then filters by orders in the past x_days. scalar gives single number, as opposed to list
    )

def average_fulfillment_time(): # read steps 1 - 5 in order to understand how this was constructed.
    print('Average fulfillment time')
    print(
        db.session.query( #1. database query 
            db.func.time( #5. convert the average value in seconds back to unixepoch format
                db.func.avg( #4. average the fulfilment times.
                    db.func.strftime('%s', Order.shipped_date) - db.func.strftime('%s', Order.order_date) #3. order date - shipped date to give the fulfillment time. needed converting from strings to seconds for math operators.
                ), 
                'unixepoch' # see point 5
            )
        ).filter(Order.shipped_date.isnot(None)).scalar() #2. filter by orders that have been shipped. scalar for a single number rather than a list.
    )

def get_customers_who_have_purchased_x_dollars(amount=500):
    print('All customers who have purchased x dollars')
    customers = db.session.query(Customer).join(Order).join(order_product).join(Product) # similar to revenue above - need to query dtabase where customer joins orders joins product (for the prices)
    .group_by(Customer).having(db.func.sum(Product.price) > amount).all() # group by customers that have a summed product prices from orders greater than the 'amount' inputter to fucntion
    for customer in customers:
        print(customer.first_name)