from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import qrcode
import io
from . import db

# Zuordnungs-Tabelle für Assets und Assignments (n:m)
asset_assignments = db.Table('asset_assignments',
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id'), primary_key=True),
    db.Column('assignment_id', db.Integer, db.ForeignKey('assignment.id'), primary_key=True)
)

# Zuordnungs-Tabelle für Assets und Manufacturers (n:m)
asset_manufacturers = db.Table('asset_manufacturers',
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id'), primary_key=True),
    db.Column('manufacturer_id', db.Integer, db.ForeignKey('manufacturer.id'), primary_key=True)
)

# Zuordnungs-Tabelle für Assets und Suppliers (n:m)
asset_suppliers = db.Table('asset_suppliers',
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id'), primary_key=True),
    db.Column('supplier_id', db.Integer, db.ForeignKey('supplier.id'), primary_key=True)
)

class Assignment(db.Model):
    """Modell für Zuordnungen von Assets"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Assignment {self.name}>'

class Manufacturer(db.Model):
    """Modell für Hersteller"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    website = db.Column(db.String(255))
    contact_info = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Manufacturer {self.name}>'

class Supplier(db.Model):
    """Modell für Lieferanten"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    website = db.Column(db.String(255))
    customer_number = db.Column(db.String(50))
    creditor_number = db.Column(db.String(50))
    description = db.Column(db.Text)
    contact_info = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Supplier {self.name}>'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default='offen')
    comment = db.Column(db.Text)
    supplier = db.relationship('Supplier', backref='orders')
    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f'<Order {self.id} von {self.supplier.name}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    asset = db.relationship('Asset')

    def __repr__(self):
        return f'<OrderItem {self.asset.name} x{self.quantity}>'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))  # URL oder Pfad zum Bild
    article_number = db.Column(db.String(100))  # Artikelnummer
    category = db.Column(db.String(50))
    ean = db.Column(db.String(13))  # EAN-Nummer
    value = db.Column(db.Float)
    status = db.Column(db.String(20), nullable=False, default='active')
    location = db.Column(db.String(100))
    serial_number = db.Column(db.String(255))
    purchase_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Beziehungen
    documents = db.relationship('Document', backref='asset', lazy=True, cascade="all, delete-orphan")
    loans = db.relationship('Loan', backref='asset', lazy=True, cascade="all, delete-orphan")
    cost_entries = db.relationship('CostEntry', backref='asset', lazy=True, cascade="all, delete-orphan")
    inventory_items = db.relationship('InventoryItem', back_populates='asset', lazy=True)
    
    # Neue n:m Beziehungen
    assignments = db.relationship('Assignment', secondary=asset_assignments, lazy='subquery',
        backref=db.backref('assets', lazy=True))
    manufacturers = db.relationship('Manufacturer', secondary=asset_manufacturers, lazy='subquery',
        backref=db.backref('assets', lazy=True))
    suppliers = db.relationship('Supplier', secondary=asset_suppliers, lazy='subquery',
        backref=db.backref('assets', lazy=True))

    @property
    def active(self):
        """Gibt zurück, ob das Asset aktiv ist"""
        return self.status == 'active'
    
    @property
    def on_loan(self):
        """Gibt zurück, ob das Asset ausgeliehen ist"""
        return self.status == 'on_loan'

    def get_status_display(self):
        """Gibt den formatierten Status zurück"""
        status_map = {
            'active': 'Aktiv',
            'on_loan': 'Ausgeliehen',
            'inactive': 'Inaktiv'
        }
        return status_map.get(self.status, self.status)

    def get_total_costs(self):
        """Berechnet die Gesamtkosten des Assets"""
        return sum(entry.amount for entry in self.cost_entries)
    
    def get_costs_by_type(self):
        """Gruppiert Kosten nach Typ"""
        costs = {}
        for entry in self.cost_entries:
            costs[entry.cost_type] = costs.get(entry.cost_type, 0) + entry.amount
        return costs
    
    def get_monthly_costs(self, months=12):
        """Berechnet die durchschnittlichen monatlichen Kosten"""
        today = datetime.utcnow()
        start_date = today - timedelta(days=30*months)
        
        recent_costs = [
            entry.amount 
            for entry in self.cost_entries 
            if entry.date >= start_date
        ]
        
        if not recent_costs:
            return 0
            
        return sum(recent_costs) / months

    def __repr__(self):
        return f'<Asset {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # scheduled, repair, inspection
    description = db.Column(db.Text, nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=True)
    completed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, overdue
    cost = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)  # Größe in Bytes
    notes = db.Column(db.Text, nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_type_display(self):
        type_map = {
            'manual': 'Handbuch',
            'invoice': 'Rechnung',
            'warranty': 'Garantie',
            'certificate': 'Zertifikat',
            'other': 'Sonstiges'
        }
        return type_map.get(self.document_type, self.document_type)

    def get_size_display(self):
        """Konvertiert Bytes in lesbare Größe"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 1024:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024
        return f"{self.size:.1f} TB"

    def can_preview(self):
        """Prüft, ob das Dokument eine Vorschau unterstützt"""
        previewable_types = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        return self.mime_type in previewable_types

    def __repr__(self):
        return f'<Document {self.title}>'

class Loan(db.Model):
    """Modell für ausgeliehene Assets"""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    borrower_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expected_return_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Loan {self.asset_id} - {self.borrower_name}>'

class CostEntry(db.Model):
    """Modell für Kosteneintrag eines Assets"""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cost_type = db.Column(db.String(50), nullable=False)  # Anschaffung, Wartung, Reparatur, etc.
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    receipt_file = db.Column(db.String(255))  # Pfad zur Belegs-Datei
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_cost_type_display(self):
        """Gibt den formatierten Kostentyp zurück"""
        cost_types = {
            'purchase': 'Anschaffung',
            'maintenance': 'Wartung',
            'repair': 'Reparatur',
            'upgrade': 'Upgrade/Erweiterung',
            'insurance': 'Versicherung',
            'other': 'Sonstiges'
        }
        return cost_types.get(self.cost_type, self.cost_type)
    
    def get_amount_display(self):
        """Formatiert den Betrag als Währung"""
        return f"{self.amount:,.2f} €"

    def __repr__(self):
        return f'<CostEntry {self.asset_id} - {self.amount}>'

class InventorySession(db.Model):
    """Eine Inventur-Session"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='planned')  # planned, active, completed
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    
    # Beziehungen
    items = db.relationship('InventoryItem', back_populates='session', cascade='all, delete-orphan')
    team = db.relationship('InventoryTeam', back_populates='session', uselist=False)

    def __repr__(self):
        return f'<InventorySession {self.name}>'

class InventoryTeam(db.Model):
    """Ein Team, das eine Inventur durchführt"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    leader_name = db.Column(db.String(100), nullable=False)
    members = db.Column(db.Text)  # Komma-separierte Liste von Teammitgliedern
    session_id = db.Column(db.Integer, db.ForeignKey('inventory_session.id'), nullable=False)
    area = db.Column(db.String(100))  # Zugewiesener Bereich für die Inventur
    
    # Beziehungen
    session = db.relationship('InventorySession', back_populates='team')

    def __repr__(self):
        return f'<InventoryTeam {self.name}>'

class InventoryItem(db.Model):
    """Ein Item in einer Inventur"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('inventory_session.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    
    # Status und Mengen
    status = db.Column(db.String(20), default='pending')  # pending, found, missing, damaged
    counted_quantity = db.Column(db.Integer)
    
    # Standort
    expected_location = db.Column(db.String(100))
    actual_location = db.Column(db.String(100))
    location_correct = db.Column(db.Boolean)
    
    # Zustand
    condition = db.Column(db.String(20))  # good, damaged, repair_needed
    condition_notes = db.Column(db.Text)
    
    # Erfassung
    counted_by = db.Column(db.String(100))
    counted_at = db.Column(db.DateTime)
    image_path = db.Column(db.String(255))
    
    # Beziehungen
    session = db.relationship('InventorySession', back_populates='items')
    asset = db.relationship('Asset', back_populates='inventory_items')

    def __repr__(self):
        return f'<InventoryItem Asset:{self.asset_id}>'
