from flask import render_template
from app.order import order

@order.route('/order/plan')
def order_plan():
    return render_template('order/plan.html')

@order.route('/order/overview')
def order_overview():
    return render_template('order/overview.html')

@order.route('/order/history')
def order_history():
    return render_template('order/history.html')
