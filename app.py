from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
import os
import csv
import io
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

app = Flask(__name__)
CORS(app)

# Data storage (in production, use a database)
DATA_FILE = 'data/business_data.json'

def load_data():
    """Load business data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        # Initial data structure
        return {
            "products": [
                {"id": 1, "name": "250ltrs open plastic Drum", "price": 2900, "stock": 10, 
                 "cost": 2000, "category": "Drums", "supplier": "Plastic Works Ltd", 
                 "min_stock": 2, "max_stock": 50, "barcode": "DRUM250OP", "unit": "piece"},
                {"id": 2, "name": "250lts close Drum", "price": 3000, "stock": 8, 
                 "cost": 2100, "category": "Drums", "supplier": "Plastic Works Ltd",
                 "min_stock": 2, "max_stock": 40, "barcode": "DRUM250CL", "unit": "piece"},
                {"id": 3, "name": "170lts Drum", "price": 2200, "stock": 15, 
                 "cost": 1500, "category": "Drums", "supplier": "Container Solutions",
                 "min_stock": 3, "max_stock": 60, "barcode": "DRUM170", "unit": "piece"},
                {"id": 4, "name": "120lts Plastic Drum", "price": 1500, "stock": 12, 
                 "cost": 1000, "category": "Drums", "supplier": "Container Solutions",
                 "min_stock": 5, "max_stock": 80, "barcode": "DRUM120", "unit": "piece"},
                {"id": 5, "name": "80lts Plastic Drum", "price": 1000, "stock": 20, 
                 "cost": 700, "category": "Drums", "supplier": "Plastic Works Ltd",
                 "min_stock": 5, "max_stock": 100, "barcode": "DRUM80", "unit": "piece"}
            ],
            "transactions": [
                {"id": 1, "date": "2024-01-15 10:30:00", "type": "sale", 
                 "amount": 5800, "customer": "John Doe", "items": [{"name": "250ltrs open plastic Drum", "quantity": 2, "price": 2900}]},
                {"id": 2, "date": "2024-01-16 14:20:00", "type": "purchase", 
                 "amount": 4200, "supplier": "Plastic Works Ltd", "description": "Restock drums"},
                {"id": 3, "date": "2024-01-17 09:15:00", "type": "sale", 
                 "amount": 2200, "customer": "Jane Smith", "items": [{"name": "170lts Drum", "quantity": 1, "price": 2200}]}
            ],
            "customers": [
                {"id": 1, "name": "John Doe", "contact": "0712345678", "email": "john@example.com", "total_spent": 5800},
                {"id": 2, "name": "Jane Smith", "contact": "0723456789", "email": "jane@example.com", "total_spent": 2200}
            ],
            "suppliers": [
                {"id": 1, "name": "Plastic Works Ltd", "contact": "0721000001", "email": "sales@plasticworks.co.ke"},
                {"id": 2, "name": "Container Solutions", "contact": "0721000002", "email": "info@containers.co.ke"}
            ],
            "notes": [],
            "settings": {"tax_rate": 16.0}
        }

def save_data(data):
    """Save business data to JSON file"""
    os.makedirs('data', exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

# PRODUCTS API
@app.route('/api/products', methods=['GET'])
def get_products():
    data = load_data()
    return jsonify(data['products'])

@app.route('/api/products', methods=['POST'])
def add_product():
    data = load_data()
    product = request.json
    product['id'] = max([p['id'] for p in data['products']], default=0) + 1
    product['last_updated'] = datetime.now().isoformat()
    data['products'].append(product)
    save_data(data)
    return jsonify(product), 201

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = load_data()
    for i, product in enumerate(data['products']):
        if product['id'] == product_id:
            updates = request.json
            updates['last_updated'] = datetime.now().isoformat()
            data['products'][i].update(updates)
            save_data(data)
            return jsonify(data['products'][i])
    return jsonify({"error": "Product not found"}), 404

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    data = load_data()
    data['products'] = [p for p in data['products'] if p['id'] != product_id]
    save_data(data)
    return jsonify({"message": "Product deleted"}), 200

# TRANSACTIONS API
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    data = load_data()
    return jsonify(data['transactions'])

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = load_data()
    transaction = request.json
    transaction['id'] = max([t['id'] for t in data['transactions']], default=0) + 1
    transaction['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Update stock for sales
    if transaction['type'] == 'sale' and 'items' in transaction:
        for item in transaction['items']:
            for product in data['products']:
                if product['name'] == item['name']:
                    product['stock'] -= item['quantity']
                    break
    
    data['transactions'].append(transaction)
    save_data(data)
    return jsonify(transaction), 201

# ANALYTICS API
@app.route('/api/analytics/sales')
def get_sales_analytics():
    data = load_data()
    days = int(request.args.get('days', 30))
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    daily_sales = {}
    product_sales = defaultdict(float)
    
    for transaction in data['transactions']:
        if transaction['type'] == 'sale':
            try:
                trans_date = datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S')
                if start_date <= trans_date <= end_date:
                    date_str = trans_date.strftime('%Y-%m-%d')
                    daily_sales[date_str] = daily_sales.get(date_str, 0) + transaction['amount']
                    
                    if 'items' in transaction:
                        for item in transaction['items']:
                            product_sales[item['name']] += item['quantity'] * item['price']
            except:
                continue
    
    # Fill missing days
    dates = []
    sales = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)
        sales.append(daily_sales.get(date_str, 0))
        current_date += timedelta(days=1)
    
    return jsonify({
        'dates': dates,
        'sales': sales,
        'top_products': sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:10],
        'total_sales': sum(sales),
        'avg_daily_sales': sum(sales) / len(sales) if sales else 0
    })

@app.route('/api/analytics/balance')
def get_balance():
    data = load_data()
    
    income = sum(t['amount'] for t in data['transactions'] if t['type'] == 'sale')
    expenses = sum(t['amount'] for t in data['transactions'] if t['type'] == 'purchase')
    stock_value = sum(p['price'] * p['stock'] for p in data['products'])
    
    return jsonify({
        'income': income,
        'expenses': expenses,
        'stock_value': stock_value,
        'gross_profit': income - expenses,
        'total_customers': len(data['customers']),
        'total_products': len(data['products'])
    })

# NOTES API
@app.route('/api/notes', methods=['GET'])
def get_notes():
    data = load_data()
    return jsonify(data['notes'])

@app.route('/api/notes', methods=['POST'])
def add_note():
    data = load_data()
    note = request.json
    note['id'] = str(uuid.uuid4())
    note['created_at'] = datetime.now().isoformat()
    note['updated_at'] = note['created_at']
    data['notes'].append(note)
    save_data(data)
    return jsonify(note), 201

@app.route('/api/notes/<note_id>', methods=['PUT'])
def update_note(note_id):
    data = load_data()
    for i, note in enumerate(data['notes']):
        if note['id'] == note_id:
            updates = request.json
            updates['updated_at'] = datetime.now().isoformat()
            data['notes'][i].update(updates)
            save_data(data)
            return jsonify(data['notes'][i])
    return jsonify({"error": "Note not found"}), 404

@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    data = load_data()
    data['notes'] = [n for n in data['notes'] if n['id'] != note_id]
    save_data(data)
    return jsonify({"message": "Note deleted"}), 200

# EXPORT API
@app.route('/api/export/csv/<export_type>')
def export_csv(export_type):
    data = load_data()
    
    if export_type == 'products':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['id', 'name', 'category', 'price', 'stock', 'cost', 'supplier'])
        writer.writeheader()
        for product in data['products']:
            writer.writerow(product)
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='products_export.csv'
        )
    
    elif export_type == 'transactions':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['id', 'date', 'type', 'amount', 'customer', 'description'])
        writer.writeheader()
        for transaction in data['transactions']:
            writer.writerow(transaction)
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='transactions_export.csv'
        )
    
    return jsonify({"error": "Invalid export type"}), 400

# BACKUP API
@app.route('/api/backup')
def backup_data():
    data = load_data()
    return send_file(
        DATA_FILE,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'business_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )

@app.route('/api/restore', methods=['POST'])
def restore_data():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if file and file.filename.endswith('.json'):
        data = json.load(file)
        save_data(data)
        return jsonify({"message": "Data restored successfully"}), 200
    
    return jsonify({"error": "Invalid file format"}), 400

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, port=5000)
