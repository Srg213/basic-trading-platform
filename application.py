import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    a = db.execute('SELECT * FROM buy WHERE username_id = ?', session['user_id'])
    b = db.execute('SELECT DISTINCT symbol FROM buy WHERE username_id = ?',session['user_id'])
    total_assets = 0
    s = []
    k= []
    t= {}
    for j in b:
        s.append(j['symbol'])
    print(s)
    for x in s:
        z = lookup(x)
        t['name'] = z['name']
        t['price'] = z['price']
        l = 0
        for i in a:
            if i['symbol'] == x:
                l += i['quantity']
        t['symbol'] = x
        t['quantity'] = l
        t['total'] = t['price'] * t['quantity']
        total_assets += float(t['total'])
        t['total'] = usd(t['total'])
        k.append(dict(t))
        print(t)
    print(k)
    cash  =  db.execute('SELECT cash FROM users WHERE id = ?', session['user_id'])[0]['cash']
    return   render_template('index.html' ,folio = k, cash = usd(cash) ,total_assets = usd(total_assets + cash))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template('buy.html')
    else:
        if not lookup(request.form.get('symbol'))  or not request.form.get('shares').isnumeric():
            return apology('Provide correct Symbol and Shares', 400)

        x = db.execute('SELECT cash FROM users WHERE id= ?',session['user_id'])
        z = lookup(request.form.get('symbol'))
        n = request.form.get('shares')
        total = int(z['price']) * int(n)
        print(x)
        if total > x[0]['cash'] :
            return apology('Insufficient cash ', 500)
        else :
            db.execute('UPDATE users SET cash = ? WHERE id = ?', x[0]['cash'] - total , session['user_id'])
            db.execute('INSERT INTO buy(username_id,symbol,price,quantity) VALUES (?,?,?,?)', session['user_id'], request.form.get('symbol').upper(), z['price'], n)
            return redirect('/')
    return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    a = db.execute('SELECT * FROM buy WHERE username_id = ?',session['user_id'])
    print(a)
    return render_template('history.html',folio=a)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == 'POST':
        if request.form.get('symbol'):
            v = lookup(request.form.get('symbol'))
            print(v)
            if v:
                return render_template('quoted.html',name =v['name'],symbol = v['symbol'],price = usd(v['price']))
            else :
                return apology('provide correct symbol', 400)
    else :
        return render_template('quote.html')
    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password") :
            return apology("must provide password", 400)

        elif  request.form.get('password')!= request.form.get('confirmation'):
            return apology('passwords do not match',400)

        try :
            rows= db.execute('INSERT INTO users(username,hash) VALUES(?,?)',request.form.get('username'),generate_password_hash(request.form.get('password')))
        except:
            return apology('Invalid',400)

        return redirect("/")
    else :
        return render_template('register.html')
    return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == 'GET':

        list =  db.execute('SELECT DISTINCT symbol FROM buy WHERE username_id = ?' , session['user_id'])
        return render_template('sell.html', list = list )

    else:
        z = lookup(request.form.get('symbol'))
        symbol = request.form.get('symbol')
        a = db.execute('SELECT quantity FROM buy WHERE symbol = ? AND username_id = ? ' ,symbol, session['user_id'])
        quantity = request.form.get('shares')
        if not quantity.isnumeric() and int(quantity()) <= 0 :
            return apology('Invalid Quantity', 400)
        l = 0
        for i in a :
            l += i['quantity']
        if l < int(quantity) :
            return apology('Invalid Quantity', 400)
        x = db.execute('SELECT cash FROM users WHERE id= ?',session['user_id'])[0]['cash']
        total = int(quantity) * z['price']
        db.execute('UPDATE users SET cash = ? WHERE id = ?', x +total , session['user_id'])
        db.execute('INSERT INTO buy(username_id,symbol,price,quantity) VALUES (?,?,?,?)', session['user_id'], request.form.get('symbol').upper(), z['price'], -int(quantity))
        return redirect('/')


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
