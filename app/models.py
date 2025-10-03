from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import qrcode
import io
from . import db
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    attachment_filename = db.Column(db.String(255))
    attachment_path = db.Column(db.String(255))
    reply_to_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    # Beziehungen
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    replies = db.relationship('Message', backref=db.backref('reply_to', remote_side=[id]), lazy='dynamic')

    def __repr__(self):
        return f'<Message {self.subject}>'

# Zuordnungs-Tabelle für Assets und Assignments (n:m)
asset_assignments = db.Table('asset_assignments',
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assignment_id', db.Integer, db.ForeignKey('assignment.id'), primary_key=True)
)

# Zuordnungs-Tabelle für Assets und Manufacturers (n:m)
asset_manufacturers = db.Table('asset_manufacturers',
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), primary_key=True),
    db.Column('manufacturer_id', db.Integer, db.ForeignKey('manufacturer.id'), primary_key=True)
)

# Zuordnungs-Tabelle für Assets und Suppliers (n:m)
asset_suppliers = db.Table('asset_suppliers',
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), primary_key=True),
    db.Column('supplier_id', db.Integer, db.ForeignKey('supplier.id'), primary_key=True)
)

class Category(db.Model):
    """Modell für Kategorien von Assets"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Category {self.name}>'

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


from datetime import datetime

class OrderComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', back_populates='comments')


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default='offen')
    comment = db.Column(db.Text)
    location = db.Column(db.String(100))  # ALT: Standort (wird migriert)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)  # NEU: Standort als ForeignKey
    tracking_number = db.Column(db.String(100))
    tracking_carrier = db.Column(db.String(50))  # AfterShip Carrier Slug, z.B. 'dhl', 'dpd', 'ups'  # NEU: Sendungsverfolgungsnummer
    expected_delivery_date = db.Column(db.DateTime, nullable=True)  # NEU: Erwartetes Lieferdatum
    cc_emails = db.Column(db.String(255), nullable=True)  # NEU: CC-E-Mail-Adressen für Bestellbenachrichtigungen
    archived = db.Column(db.Boolean, default=False)  # NEU: Für Archivierung
    pdf_path = db.Column(db.String(255), nullable=True)  # Pfad zur PDF-Bestelldatei
    supplier = db.relationship('Supplier', backref='orders')
    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan", lazy=True)
    location_obj = db.relationship('Location', backref='orders')  # Relationship für Standort

    def __repr__(self):
        return f'<Order {self.id} von {self.supplier.name}>'

Order.comments = db.relationship('OrderComment', back_populates='order', lazy='dynamic', cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    asset = db.relationship('Asset')
    serial_number = db.Column(db.String(100), nullable=True)  # Serial Number (optional)

    def __repr__(self):
        return f'<OrderItem {self.asset.name} x{self.quantity}>'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))  # URL oder Pfad zum Bild
    article_number = db.Column(db.String(100))  # Artikelnummer
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref='assets')
    ean = db.Column(db.String(13))  # EAN-Nummer
    value = db.Column(db.Float)
    status = db.Column(db.String(20), nullable=False, default='active')
    archived_at = db.Column(db.DateTime, nullable=True)  # Zeitpunkt der Archivierung
    location = db.Column(db.String(100))  # Altes Feld für Migration
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)  # NEU: FK auf Location
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

# Mapping-Tabelle: Rollen und Rechte (n:m)
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.relationship('Permission', secondary=role_permissions, backref=db.backref('roles', lazy='dynamic'))
    users = db.relationship('User', back_populates='role')

    def __repr__(self):
        return f'<Role {self.name}>'

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    failed_logins = db.Column(db.Integer, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', back_populates='users')
    vorname = db.Column(db.String(80))
    nachname = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    profile_image = db.Column(db.String(255))  # Dateiname oder URL zum Profilbild
    street = db.Column(db.String(120))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(80))
    phone = db.Column(db.String(40))

    @property
    def is_admin(self):
        return self.role is not None and self.role.name.lower() == 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Passwort-Reset-Token Methoden ---
    def get_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        except SignatureExpired:
            return None  # Token abgelaufen
        except BadSignature:
            return None  # Token ungültig
        from .models import User
        return User.query.get(data['user_id'])


class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
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
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
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
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    borrower_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expected_return_date = db.Column(db.Date, nullable=True)
    actual_return_date = db.Column(db.Date)  # Umbenennung von return_date für Konsistenz
    return_date = db.Column(db.Date)  # Legacy-Feld beibehalten
    notes = db.Column(db.Text)
    signature = db.Column(db.Text)  # Base64 PNG - Unterschrift Mitarbeiter
    signature_employer = db.Column(db.Text)  # Base64 PNG - Unterschrift Arbeitgeber
    pdf_filename = db.Column(db.String(255))  # PDF-Dateiname
    pdf_path = db.Column(db.String(255))  # PDF-Pfad
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship zu Asset (overlaps mit Asset.loans und Loan.asset)
    loaned_asset = db.relationship('Asset', foreign_keys=[asset_id], overlaps="asset,loans")

    def __repr__(self):
        return f'<Loan {self.asset_id} - {self.borrower_name}>'

class CostEntry(db.Model):
    """Modell für Kosteneintrag eines Assets"""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
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
    __tablename__ = 'inventory_planning'  # MD3 table name
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))  # ALT: Standort (wird migriert)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)  # NEU: Standort als ForeignKey
    status = db.Column(db.String(20), default='planned')  # planned, active, completed
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    
    # MISSING ATTRIBUTES - ADD THESE FOR COMPATIBILITY
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)  # When inventory was completed
    
    # Beziehungen
    items = db.relationship('InventoryItem', back_populates='session', cascade='all, delete-orphan')
    team = db.relationship('InventoryTeam', back_populates='session', uselist=False)
    location = db.relationship('Location', foreign_keys=[location_id])  # Relationship für Standort
    created_by = db.relationship('User', foreign_keys=[created_by_user_id], backref='created_inventory_sessions')

    def __repr__(self):
        return f'<InventorySession {self.name}>'

class InventoryTeam(db.Model):
    """Ein Team, das eine Inventur durchführt"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    leader_name = db.Column(db.String(100), nullable=False)
    members = db.Column(db.Text)  # Komma-separierte Liste von Teammitgliedern
    session_id = db.Column(db.Integer, db.ForeignKey('inventory_planning.id'), nullable=False)
    area = db.Column(db.String(100))  # Zugewiesener Bereich für die Inventur
    
    # Beziehungen
    session = db.relationship('InventorySession', back_populates='team')

    def __repr__(self):
        return f'<InventoryTeam {self.name}>'

from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import JSON

# --- Multi-Asset-Loan (Sammelausleihe) ---
class MultiLoan(db.Model):
    __tablename__ = 'multi_loan'
    id = db.Column(db.Integer, primary_key=True)
    borrower_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expected_return_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
    signature = db.Column(db.Text)  # Base64 PNG
    signature_employer = db.Column(db.Text)  # Base64 PNG
    pdf_filename = db.Column(db.String(255))
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assets = db.relationship('Asset', secondary='multi_loan_asset', backref='multi_loans')

    def __repr__(self):
        return f'<MultiLoan {self.id} - {self.borrower_name}>'

class MultiLoanAsset(db.Model):
    __tablename__ = 'multi_loan_asset'
    multi_loan_id = db.Column(db.Integer, db.ForeignKey('multi_loan.id'), primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), primary_key=True)


class AssetLog(db.Model):
    """Protokolliert Aktionen auf Assets (Archivieren, Wiederherstellen, Löschen, Anlegen, Bearbeiten)"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(30), nullable=False)  # z.B. 'archiviert', 'wiederhergestellt', 'gelöscht', 'angelegt', 'bearbeitet'
    details = db.Column(db.Text)  # z.B. Änderungen als JSON/Text
    ip_address = db.Column(db.String(45))

    user = db.relationship('User', backref='asset_logs')
    asset = db.relationship('Asset', backref=db.backref('logs', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<AssetLog {self.action} by {self.username} on asset {self.asset_id}>'


class InventoryItem(db.Model):
    """Ein Item in einer Inventur"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('inventory_planning.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    
    # Status und Mengen
    status = db.Column(db.String(20), default='pending')  # pending, found, missing, damaged
    counted_quantity = db.Column(db.Integer)
    expected_quantity = db.Column(db.Integer)  # Soll-Menge laut System
    
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

    # JSON-Feld für Seriennummer-Zustände
    serial_statuses = db.Column(MutableList.as_mutable(JSON), default=list)


    def __repr__(self):
        return f'<InventoryItem Asset:{self.asset_id}>'

class Location(db.Model):
    """Modell für Standorte (Stores, Filialen, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    street = db.Column(db.String(255))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    size_sqm = db.Column(db.Float)  # Ladengröße in Quadratmetern
    seats = db.Column(db.Integer)   # Sitzplätze
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))  # Foto/Bild vom Standort (optional)
    latitude = db.Column(db.Float)  # Für Kartenanzeige
    longitude = db.Column(db.Float)
    # Google-Integration für mobile Navigation und Bewertungen
    google_place_id = db.Column(db.String(255))  # Google Places ID für Bewertungen
    google_rating = db.Column(db.Float)  # Google-Bewertung (1.0-5.0)
    google_reviews_count = db.Column(db.Integer)  # Anzahl der Google-Bewertungen
    google_maps_url = db.Column(db.String(500))  # Direkte Google Maps URL
    # Inventur-Informationen
    last_inventory_date = db.Column(db.DateTime, nullable=True)
    inventory_status = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assets = db.relationship('Asset', backref='location_obj', lazy=True)
    images = db.relationship('LocationImage', backref='location', lazy=True, cascade='all, delete-orphan')
    floorplans = db.relationship('LocationFloorplan', backref='location', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Location {self.name}>'

class LocationImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    comment = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploader = db.Column(db.String(100))

    def __repr__(self):
        return f'<LocationImage {self.id}>'


class LocationFloorplan(db.Model):
    """Meta-Informationen zu Grundriss-Sammlungen pro Standort."""
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    revisions = db.relationship(
        'LocationFloorplanRevision',
        backref='floorplan',
        order_by='LocationFloorplanRevision.version_number',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<LocationFloorplan {self.name} (Location {self.location_id})>'


class LocationFloorplanRevision(db.Model):
    """Konkrete Version eines Grundrisses (Bild/PDF + Maßstab)."""
    id = db.Column(db.Integer, primary_key=True)
    floorplan_id = db.Column(db.Integer, db.ForeignKey('location_floorplan.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    filename = db.Column(db.String(255), nullable=False)
    preview_filename = db.Column(db.String(255))
    mimetype = db.Column(db.String(120), nullable=False)
    scale_line_length_px = db.Column(db.Float)
    scale_real_length_cm = db.Column(db.Float)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assets = db.relationship(
        'LocationFloorplanAsset',
        backref='revision',
        lazy=True,
        cascade='all, delete-orphan'
    )
    autosaves = db.relationship(
        'LocationFloorplanAutosave',
        backref='revision',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<LocationFloorplanRevision {self.id} v{self.version_number}>'


class LocationFloorplanAsset(db.Model):
    """Position eines Assets innerhalb einer Floorplan-Revision."""
    id = db.Column(db.Integer, primary_key=True)
    revision_id = db.Column(db.Integer, db.ForeignKey('location_floorplan_revision.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    position_x = db.Column(db.Float, nullable=False)
    position_y = db.Column(db.Float, nullable=False)
    rotation = db.Column(db.Float, default=0.0)
    display_label = db.Column(db.String(150))
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = db.relationship('Asset', lazy=True)

    def __repr__(self):
        return (
            f'<LocationFloorplanAsset asset={self.asset_id} '
            f'revision={self.revision_id} ({self.position_x}, {self.position_y})>'
        )


class LocationFloorplanAutosave(db.Model):
    """Automatisch gesicherter Arbeitsstand einer Revision."""
    id = db.Column(db.Integer, primary_key=True)
    revision_id = db.Column(db.Integer, db.ForeignKey('location_floorplan_revision.id'), nullable=False)
    payload = db.Column(db.Text, nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LocationFloorplanAutosave revision={self.revision_id} at {self.saved_at}>'

class OrderTemplate(db.Model):
    """Modell für Bestellvorlagen, die vom Benutzer gespeichert werden können"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Beziehungen
    supplier = db.relationship('Supplier', backref='order_templates')
    location = db.relationship('Location', backref='order_templates')
    items = db.relationship('OrderTemplateItem', backref='template', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<OrderTemplate {self.name}>'

class OrderTemplateItem(db.Model):
    """Ein einzelnes Asset in einer Bestellvorlage"""
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('order_template.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    # Beziehungen
    asset = db.relationship('Asset')
    
    def __repr__(self):
        return f'<OrderTemplateItem {self.id} for template {self.template_id} with asset {self.asset_id}>'

# ============================================================================
# KALENDER & EVENTS
# ============================================================================

# Event-Typen Konstanten
EVENT_TYPE_DELIVERY = 'delivery'
EVENT_TYPE_INVENTORY = 'inventory'
EVENT_TYPE_MANUAL = 'manual'

# Event-Status Konstanten
EVENT_STATUS_PLANNED = 'planned'
EVENT_STATUS_CONFIRMED = 'confirmed'
EVENT_STATUS_COMPLETED = 'completed'
EVENT_STATUS_CANCELLED = 'cancelled'

# Reminder-Status Konstanten
REMINDER_STATUS_PENDING = 'pending'
REMINDER_STATUS_DELIVERED = 'delivered'
REMINDER_STATUS_READ = 'read'

class CalendarEvent(db.Model):
    """Kalender-Event für Liefertermine, Inventur-Termine, etc."""
    __tablename__ = 'calendar_event'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime)
    
    # Event-Typ: 'delivery', 'inventory', 'manual'
    event_type = db.Column(db.String(50), default=EVENT_TYPE_MANUAL)
    
    # Status: 'planned', 'confirmed', 'completed', 'cancelled'
    status = db.Column(db.String(50), default=EVENT_STATUS_PLANNED)
    
    # Verknüpfung zur Bestellung (optional)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    
    # Verknüpfung zu Inventur-Session (optional)
    inventory_session_id = db.Column(db.Integer, db.ForeignKey('inventory_planning.id'))
    
    # Erstellt von Benutzer
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Beziehungen
    order = db.relationship('Order', backref='calendar_events')
    inventory_session = db.relationship('InventorySession', backref='calendar_events')
    created_by = db.relationship('User', backref='created_events')
    reminders = db.relationship('EventReminder', backref='event', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CalendarEvent {self.id}: {self.title} ({self.event_type})>'

class EventReminder(db.Model):
    """Erinnerung für ein Kalender-Event"""
    __tablename__ = 'event_reminder'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('calendar_event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Wann soll erinnert werden (z.B. 1 Tag vorher)
    remind_at = db.Column(db.DateTime, nullable=False)
    
    # Status: 'pending', 'delivered', 'read'
    status = db.Column(db.String(50), default=REMINDER_STATUS_PENDING)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    
    # Beziehungen
    user = db.relationship('User', backref='event_reminders')
    
    def __repr__(self):
        return f'<EventReminder {self.id} for Event {self.event_id}, User {self.user_id}>'
