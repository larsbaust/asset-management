// JS für CSV-Upload, Vorschau und Mapping
$(document).ready(function() {
  $('#csvFile').on('change', function(e) {
    let file = e.target.files[0];
    if (!file) return;
    let reader = new FileReader();
    reader.onload = function(e) {
      let text = e.target.result;
      $.ajax({
        url: '/preview_csv',
        method: 'POST',
        data: {csv_text: text},
        success: function(resp) {
          $('#csv-preview-section').show();
          $('#csv-preview-table').html(resp.preview_html);
          $('#csv-mapping-form').html(resp.mapping_html);
          $('#import-csv-btn').prop('disabled', false);
        },
        error: function() {
          alert('Fehler beim Verarbeiten der CSV-Datei.');
        }
      });
    };
    reader.readAsText(file);
  });

  $('#import-csv-btn').on('click', function() {
    let mapping = {};
    $('#csv-mapping-form select').each(function() {
      mapping[$(this).attr('name')] = $(this).val();
    });
    $.ajax({
      url: '/import_csv',
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({mapping: mapping}),
      success: function(resp) {
        location.reload(); // Nach Import neu laden oder Tabelle aktualisieren
      },
      error: function() {
        alert('Fehler beim Import.');
      }
    });
  });
});
