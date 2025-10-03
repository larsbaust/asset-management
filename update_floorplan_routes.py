from pathlib import Path
import textwrap

main_path = Path(r"c:\Users\baust\CascadeProjects\Assed Managemend\app\main.py")
text = main_path.read_text(encoding="utf-8")
marker = "@main.route('/')"
if marker not in text:
    raise SystemExit('marker not found')
insert_idx = text.index(marker)
block = textwrap.dedent('''


def serialize_floorplan_asset(asset_entry: LocationFloorplanAsset) -> dict:
    asset = asset_entry.asset
    return {
        'id': asset_entry.id,
        'asset_id': asset_entry.asset_id,
        'position_x': asset_entry.position_x,
        'position_y': asset_entry.position_y,
        'rotation': asset_entry.rotation,
        'display_label': asset_entry.display_label,
        'metadata': json.loads(asset_entry.metadata_json) if asset_entry.metadata_json else None,
        'created_at': asset_entry.created_at.isoformat() if asset_entry.created_at else None,
        'updated_at': asset_entry.updated_at.isoformat() if asset_entry.updated_at else None,
        'asset': {
            'name': asset.name if asset else None,
            'status': asset.status if asset else None,
            'serial_number': getattr(asset, 'serial_number', None) if asset else None,
            'category': asset.category.name if asset and asset.category else None,
        } if asset else None,
    }


def serialize_floorplan_revision(revision: LocationFloorplanRevision, include_assets: bool = True) -> dict:
    floorplan = revision.floorplan
    location_id = floorplan.location_id if floorplan else None
    file_url = url_for('main.get_floorplan_file', location_id=location_id, filename=revision.filename) if location_id else None
    preview_url = (
        url_for('main.get_floorplan_file', location_id=location_id, filename=revision.preview_filename)
        if location_id and revision.preview_filename
        else None
    )
    latest_autosave = None
    if revision.autosaves:
        latest = max(revision.autosaves, key=lambda a: a.saved_at or datetime.min)
        latest_autosave = {
            'id': latest.id,
            'saved_at': latest.saved_at.isoformat() if latest.saved_at else None,
        }

    return {
        'id': revision.id,
        'version_number': revision.version_number,
        'filename': revision.filename,
        'file_url': file_url,
        'preview_filename': revision.preview_filename,
        'preview_url': preview_url,
        'mimetype': revision.mimetype,
        'scale_line_length_px': revision.scale_line_length_px,
        'scale_real_length_cm': revision.scale_real_length_cm,
        'metadata': json.loads(revision.metadata_json) if revision.metadata_json else None,
        'created_at': revision.created_at.isoformat() if revision.created_at else None,
        'updated_at': revision.updated_at.isoformat() if revision.updated_at else None,
        'assets': [serialize_floorplan_asset(asset) for asset in revision.assets] if include_assets else None,
        'latest_autosave': latest_autosave,
    }


def serialize_floorplan(floorplan: LocationFloorplan, include_revisions: bool = True) -> dict:
    revisions = floorplan.revisions or []
    latest_revision = revisions[-1] if revisions else None
    return {
        'id': floorplan.id,
        'location_id': floorplan.location_id,
        'name': floorplan.name,
        'description': floorplan.description,
        'is_archived': floorplan.is_archived,
        'created_at': floorplan.created_at.isoformat() if floorplan.created_at else None,
        'updated_at': floorplan.updated_at.isoformat() if floorplan.updated_at else None,
        'latest_revision': serialize_floorplan_revision(latest_revision) if latest_revision else None,
        'revisions': [serialize_floorplan_revision(rev) for rev in revisions] if include_revisions else None,
    }


def ensure_asset_belongs_to_location(asset: Asset, location_id: int) -> bool:
    if not asset:
        return False
    if asset.location_id == location_id:
        return True
    if asset.location and asset.location.strip() == str(location_id):
        return True
    return False


@main.route('/uploads/floorplans/<int:location_id>/<path:filename>')
@login_required
def get_floorplan_file(location_id, filename):
    directory = get_floorplan_upload_dir(location_id)
    return send_from_directory(directory, filename)


@main.route('/api/locations/<int:location_id>/floorplans', methods=['GET', 'POST'])
@login_required
def api_location_floorplans(location_id):
    location = Location.query.get_or_404(location_id)

    if request.method == 'GET':
        include_archived = request.args.get('archived') == '1'
        floorplans = [
            serialize_floorplan(fp)
            for fp in location.floorplans
            if include_archived or not fp.is_archived
        ]
        return jsonify({'floorplans': floorplans})

    name = (request.form.get('name') or '').strip()
    description = (request.form.get('description') or '').strip() or None
    file = request.files.get('file')

    if not name:
        return jsonify({'error': 'Name darf nicht leer sein.'}), 400

    if not file or file.filename == '':
        return jsonify({'error': 'Bitte eine Datei hochladen.'}), 400

    if not allowed_floorplan_file(file.filename):
        return jsonify({'error': 'Dateityp wird nicht unterstützt.'}), 400

    storage_dir = get_floorplan_upload_dir(location_id)
    stored_filename = build_floorplan_filename(file.filename)
    absolute_path = os.path.join(storage_dir, stored_filename)
    file.save(absolute_path)

    floorplan = LocationFloorplan(
        location_id=location.id,
        name=name,
        description=description,
    )
    db.session.add(floorplan)
    db.session.flush()

    revision = LocationFloorplanRevision(
        floorplan_id=floorplan.id,
        version_number=1,
        filename=stored_filename,
        mimetype=file.mimetype or 'application/octet-stream',
    )
    db.session.add(revision)
    db.session.commit()

    return jsonify({'floorplan': serialize_floorplan(floorplan)}), 201


@main.route('/api/floorplans/<int:floorplan_id>', methods=['PATCH', 'DELETE'])
@login_required
def api_floorplan_detail(floorplan_id):
    floorplan = LocationFloorplan.query.get_or_404(floorplan_id)

    if request.method == 'DELETE':
        db.session.delete(floorplan)
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json() or {}
    if 'name' in data:
        floorplan.name = data['name'].strip()
    if 'description' in data:
        floorplan.description = data['description'].strip() or None
    if 'is_archived' in data:
        floorplan.is_archived = bool(data['is_archived'])

    db.session.commit()
    return jsonify({'floorplan': serialize_floorplan(floorplan)})


@main.route('/api/floorplans/<int:floorplan_id>/revisions', methods=['POST'])
@login_required
def api_floorplan_revisions(floorplan_id):
    floorplan = LocationFloorplan.query.get_or_404(floorplan_id)

    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'Bitte eine Datei hochladen.'}), 400

    if not allowed_floorplan_file(file.filename):
        return jsonify({'error': 'Dateityp wird nicht unterstützt.'}), 400

    storage_dir = get_floorplan_upload_dir(floorplan.location_id)
    stored_filename = build_floorplan_filename(file.filename)
    absolute_path = os.path.join(storage_dir, stored_filename)
    file.save(absolute_path)

    latest_version = (
        db.session.query(func.max(LocationFloorplanRevision.version_number))
        .filter_by(floorplan_id=floorplan.id)
        .scalar()
        or 0
    )

    revision = LocationFloorplanRevision(
        floorplan_id=floorplan.id,
        version_number=latest_version + 1,
        filename=stored_filename,
        mimetype=file.mimetype or 'application/octet-stream',
    )
    db.session.add(revision)
    db.session.commit()

    return jsonify({'revision': serialize_floorplan_revision(revision)})


@main.route('/api/floorplan-revisions/<int:revision_id>', methods=['PATCH', 'DELETE'])
@login_required
def api_floorplan_revision_detail(revision_id):
    revision = LocationFloorplanRevision.query.get_or_404(revision_id)

    if request.method == 'DELETE':
        db.session.delete(revision)
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json() or {}
    if 'scale_line_length_px' in data:
        revision.scale_line_length_px = float(data['scale_line_length_px']) if data['scale_line_length_px'] is not None else None
    if 'scale_real_length_cm' in data:
        revision.scale_real_length_cm = float(data['scale_real_length_cm']) if data['scale_real_length_cm'] is not None else None
    if 'metadata' in data:
        revision.metadata_json = json.dumps(data['metadata']) if data['metadata'] is not None else None

    db.session.commit()
    return jsonify({'revision': serialize_floorplan_revision(revision)})


@main.route('/api/floorplan-revisions/<int:revision_id>/assets', methods=['POST'])
@login_required
def api_floorplan_revision_add_asset(revision_id):
    revision = LocationFloorplanRevision.query.get_or_404(revision_id)
    data = request.get_json() or {}

    asset_id = data.get('asset_id')
    if not asset_id:
        return jsonify({'error': 'asset_id fehlt'}), 400

    asset = Asset.query.get(asset_id)
    if not ensure_asset_belongs_to_location(asset, revision.floorplan.location_id):
        return jsonify({'error': 'Asset gehört nicht zu diesem Standort.'}), 400

    position_x = float(data.get('position_x', 0.5))
    position_y = float(data.get('position_y', 0.5))
    rotation = float(data.get('rotation', 0.0))
    display_label = data.get('display_label')
    metadata = data.get('metadata')

    asset_entry = LocationFloorplanAsset(
        revision_id=revision.id,
        asset_id=asset_id,
        position_x=position_x,
        position_y=position_y,
        rotation=rotation,
        display_label=display_label,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
    )
    db.session.add(asset_entry)
    db.session.commit()

    return jsonify({'asset': serialize_floorplan_asset(asset_entry)}), 201


@main.route('/api/floorplan-assets/<int:asset_entry_id>', methods=['PATCH', 'DELETE'])
@login_required
def api_floorplan_asset_detail(asset_entry_id):
    asset_entry = LocationFloorplanAsset.query.get_or_404(asset_entry_id)

    if request.method == 'DELETE':
        db.session.delete(asset_entry)
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json() or {}
    if 'position_x' in data:
        asset_entry.position_x = float(data['position_x'])
    if 'position_y' in data:
        asset_entry.position_y = float(data['position_y'])
    if 'rotation' in data:
        asset_entry.rotation = float(data['rotation'])
    if 'display_label' in data:
        asset_entry.display_label = data['display_label']
    if 'metadata' in data:
        asset_entry.metadata_json = json.dumps(data['metadata']) if data['metadata'] is not None else None

    db.session.commit()
    return jsonify({'asset': serialize_floorplan_asset(asset_entry)})


@main.route('/api/floorplan-revisions/<int:revision_id>/autosave', methods=['GET', 'POST'])
@login_required
def api_floorplan_autosave(revision_id):
    revision = LocationFloorplanRevision.query.get_or_404(revision_id)

    if request.method == 'GET':
        autosave = (
            LocationFloorplanAutosave.query.filter_by(revision_id=revision.id)
            .order_by(LocationFloorplanAutosave.saved_at.desc())
            .first()
        )
        if not autosave:
            return jsonify({'autosave': None})
        return jsonify({
            'autosave': {
                'id': autosave.id,
                'payload': json.loads(autosave.payload),
                'saved_at': autosave.saved_at.isoformat() if autosave.saved_at else None,
            }
        })

    data = request.get_json() or {}
    payload = data.get('payload')
    if payload is None:
        return jsonify({'error': 'payload fehlt'}), 400

    payload_str = json.dumps(payload) if not isinstance(payload, str) else payload

    autosave = LocationFloorplanAutosave(
        revision_id=revision.id,
        payload=payload_str,
    )
    db.session.add(autosave)
    db.session.flush()

    autosaves = (
        LocationFloorplanAutosave.query.filter_by(revision_id=revision.id)
        .order_by(LocationFloorplanAutosave.saved_at.desc())
        .all()
    )
    for obsolete in autosaves[10:]:
        db.session.delete(obsolete)

    db.session.commit()

    return jsonify({
        'autosave': {
            'id': autosave.id,
            'saved_at': autosave.saved_at.isoformat() if autosave.saved_at else None,
        }
    }), 201
''');
main_path.write_text(text[:insert_idx] + block + text[insert_idx:], encoding="utf-8")
print('Floorplan routes inserted')
