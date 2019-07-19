import tornado.ioloop
import tornado.web
import aiopg
import psycopg2
import uuid
import json
import datetime
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.web
import tornado.util

from tornado.options import define, options

define("port", default=8888, help="Run on the given port", type=int)
define("db_host", default="127.0.0.1", help="Postgres host")
define("db_port", default=5432, help="Postgres port")
define("db_database", default="postgres", help="Postgres database")
define("db_user", default="postgres", help="Database user")
define("db_password", default="postgres", help="Database password")


class NoResultError(Exception):
    pass


async def create_tables(db):
    try:
        with (await db.cursor()) as cur:
            await cur.execute("SELECT COUNT(*) FROM orders LIMIT 1")
            await cur.fetchone()
    except psycopg2.ProgrammingError:
        with open("schema.sql") as f:
            schema = f.read()
        with (await db.cursor()) as cur:
            await cur.execute(schema)


class Application(tornado.web.Application):
    def __init__(self, db):
        self.db = db
        handlers = [
            (r"/", HomeHandler),
            (r"/api/v1/users", UserHandler),
            (r"/api/v1/orders", OrderHandler),
            (r"/api/v1/products", ProductHandler),
            (r"/api/v1/categories", CategoryHandler),
        ]
        super(Application, self).__init__(handlers)


class BaseHandler(tornado.web.RequestHandler):
    def row_to_obj(self, row, cur):
        """Convert a SQL row to an object supporting dict and attribute access."""
        obj = tornado.util.ObjectDict()
        for val, desc in zip(row, cur.description):
            obj[desc.name] = str(val) if type(val) is uuid.UUID else val
        return obj

    async def execute(self, stmt, *args):
        with (await self.application.db.cursor()) as cur:
            await cur.execute(stmt, args)

    async def query(self, stmt, *args):
        with (await self.application.db.cursor()) as cur:
            await cur.execute(stmt, args)
            return [self.row_to_obj(row, cur) for row in await cur.fetchall()]

    async def queryone(self, stmt, *args):
        results = await self.query(stmt, *args)
        if len(results) == 0:
            raise NoResultError()
        elif len(results) > 1:
            raise ValueError("Expected 1 result, got %d" % len(results))
        return results[0]

    def response_builder(self, data):
        return {'version': '1.0.0',
                'timestamp': datetime.datetime.now().isoformat(),
                'data': data}

    def read_json(self, body):
        return json.loads(body)


async def main():
    tornado.options.parse_command_line()

    # Create the global connection pool.
    async with aiopg.create_pool(
            host=options.db_host,
            port=options.db_port,
            user=options.db_user,
            password=options.db_password,
            dbname=options.db_database,
    ) as db:
        await create_tables(db)
        app = Application(db)
        app.listen(options.port)

        shutdown_event = tornado.locks.Event()
        await shutdown_event.wait()


class HomeHandler(BaseHandler):
    async def get(self):
        data = self.response_builder(
            """
            Welcome to the app, The below routes are available
            1. users - GET/POST/PUT /api/v1/users
            2. products - GET/POST/PUT /api/v1/products
            3. orders - GET/POST /api/v1/products
            """
        )
        self.write(data)


class UserHandler(BaseHandler):

    async def get(self):
        user = await self.queryone("SELECT * from users where id=%s", self.get_argument("id"))
        if not user:
            users = await self.query("SELECT * from users")
            if not users:
                raise tornado.web.HTTPError(404)
            self.write(self.response_builder(users))
            return
        self.write(self.response_builder(user))

    async def post(self):
        data = self.read_json(self.request.body)
        name = data['name']
        email = data['email']
        mobile = data['mobile']
        await self.execute("""
            INSERT INTO users(id, name, email, mobile) 
            VALUES(%s, %s, %s, %s   )
        """, uuid.uuid4(), name, email, mobile)
        self.write(self.response_builder("Request sent successfully"))

    async def put(self):
        data = self.read_json(self.request.body)
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)

        await self.queryone(
            "SELECT * FROM users WHERE id = %s", id
        )

        await self.execute(
            "UPDATE users SET name = %s, email = %s, mobile = %s "
            "WHERE id = %s",
            data['name'],
            data['email'],
            data['mobile'],
            id,
        )

    async def delete(self):
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)
        await self.execute("DELETE FROM users where id=%s", id)
        self.write(self.response_builder("Request sent successfully"))


class ProductHandler(BaseHandler):
    async def get(self):
        product = await self.queryone("SELECT * from products where id=%s", self.get_argument("id"))
        if not product:
            products = await self.query("SELECT * from products")
            if not products:
                raise tornado.web.HTTPError(404)
            self.write(self.response_builder(products))
            return
        self.write(self.response_builder(product))

    async def post(self):
        data = self.read_json(self.request.body)
        name = data['name']
        price = data['price']
        type = uuid.UUID(data['type'])
        await self.execute("""
            INSERT INTO products(id, name, price, type) 
            VALUES(%s, %s, %s, %s)
        """, uuid.uuid4(), name, price, type)
        self.write(self.response_builder("Request sent successfully"))

    async def put(self):
        data = self.read_json(self.request.body)
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)

        await self.queryone(
            "SELECT * FROM products WHERE id = %s", id
        )

        await self.execute(
            "UPDATE products SET name = %s, price = %s type = %s"
            "WHERE id = %s",
            data['name'],
            data['price'],
            data['type'],
            id,
        )

    async def delete(self):
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)
        await self.execute("DELETE FROM products where id=%s", id)
        self.write(self.response_builder("Request sent successfully"))


class CategoryHandler(BaseHandler):
    async def get(self):
        category = await self.queryone("SELECT * from categories where id=%s", self.get_argument("id"))
        if not category:
            categories = await self.query("SELECT * from categories")
            if not categories:
                raise tornado.web.HTTPError(404)
            self.write(self.response_builder(categories))
            return
        self.write(self.response_builder(category))

    async def post(self):
        data = self.read_json(self.request.body)
        category = data['category']
        await self.execute("""
            INSERT INTO categories(id, category) 
            VALUES(%s, %s)
        """, uuid.uuid4(), category)
        self.write(self.response_builder("Request sent successfully"))

    async def put(self):
        data = self.read_json(self.request.body)
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)

        await self.queryone(
            "SELECT * FROM categories WHERE id = %s", id
        )

        await self.execute(
            "UPDATE categories SET category = %s"
            "WHERE id = %s",
            data['category'],
            id,
        )

    async def delete(self):
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)
        await self.execute("DELETE FROM categories where id=%s", id)
        self.write(self.response_builder("Request sent successfully"))


class OrderHandler(BaseHandler):
    async def get(self):
        order = await self.queryone("SELECT * from orders where id=%s", self.get_argument("id"))
        if not order:
            orders = await self.query("SELECT * from orders")
            if not orders:
                raise tornado.web.HTTPError(404)
            self.write(self.response_builder(orders))
            return
        self.write(self.response_builder(order))

    async def get(self, order_id):
        order = self.queryone("SELECT * from orders where id=%s", uuid.UUID(order_id))
        if not order:
            raise tornado.web.HTTPError(404)
        self.write(self.response_builder(order))

    async def post(self):
        data = self.read_json(self.request.body)
        product_id = uuid.UUID(data['product_id'])
        user_id = uuid.UUID(data['user_id'])
        await self.execute("""
            INSERT INTO orders(purchased_at, product_id, user_id) 
            VALUES(CURRENT_TIMESTAMP, %s, %s)
        """, product_id, user_id)
        self.write(self.response_builder("Request sent successfully"))

    async def put(self):
        data = self.read_json(self.request.body)
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)

        await self.queryone(
            "SELECT * FROM orders WHERE id = %s", id
        )

        await self.execute(
            "UPDATE orders SET product_id = %s, user_id=%s"
            "WHERE id = %s",
            data['product_id'],
            data['user_id'],
            id,
        )

    async def delete(self):
        id = self.get_argument("id", None)
        if not id:
            tornado.web.HTTPError(400)
        await self.execute("DELETE FROM categories where id=%s", id)
        self.write(self.response_builder("Request sent successfully"))


if __name__ == "__main__":
    tornado.ioloop.IOLoop.current().run_sync(main)