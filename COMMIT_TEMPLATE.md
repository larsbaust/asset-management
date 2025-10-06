# 📝 Git Commit Template für Asset Management System

## 🎯 Struktur für detaillierte Commits

Verwende diese Vorlage für alle Feature-Commits, um eine konsistente und detaillierte Dokumentation zu gewährleisten.

---

## 📋 Commit-Message-Vorlage

```
[EMOJI] [TYP]: [Kurzbeschreibung in einem Satz]

📋 HAUPTFEATURES:
- [Feature 1]
- [Feature 2]
- [Feature 3]

🎨 UI/UX-VERBESSERUNGEN:
- [Verbesserung 1]
- [Verbesserung 2]
- [Verbesserung 3]

📊 DETAILS-INHALTE:
- [Detail 1]
- [Detail 2]
- [Detail 3]

🔧 TECHNISCHE DETAILS:
- Template/Datei: [Pfad]
- Neue Funktionen: [Funktion 1, Funktion 2]
- CSS/JS-Änderungen: [Beschreibung]
- Animationen/Transitions: [Details]

📱 MOBILE-OPTIMIERUNG: (falls relevant)
- [Optimierung 1]
- [Optimierung 2]

💡 VERWENDUNGSZWECK:
[Beschreibe, wofür diese Änderung gedacht ist und wie sie verwendet werden soll]
```

---

## 🏷️ Emoji-Konvention

### **Hauptkategorien:**
- ✨ **Feature** - Neue Funktionalität
- 🔧 **Fix** - Bugfix
- 📱 **Mobile** - Mobile-Optimierung
- 🎨 **UI** - Design/Styling-Änderung
- 🔒 **Security** - Sicherheitsverbesserung
- 💡 **Improvement** - Verbesserung bestehender Features
- 🚀 **Performance** - Performance-Optimierung
- 📝 **Docs** - Dokumentation
- 🐛 **Bugfix** - Fehlerbehebung
- ⚡ **Enhancement** - Funktionserweiterung
- 📦 **Package** - Abhängigkeiten/Packages
- 🔍 **Search** - Such-/Filter-Funktionalität
- ♻️ **Refactor** - Code-Refactoring
- 🔥 **Remove** - Code/Features entfernt
- 💾 **Save** - Speicher-Funktionalität
- 🌐 **i18n** - Internationalisierung
- 📊 **Analytics** - Analytics/Tracking
- 🎯 **Focus** - Fokus auf bestimmte Funktionalität

---

## 📐 Beispiel-Commits

### **Feature-Commit:**
```
✨ Feature: Expandierbare Changelog-Cards mit MD3-Timeline & Icon-Details

📋 HAUPTFEATURES:
- Expandierbare Cards mit Click-to-Expand Funktionalität
- Timeline-Visualisierung mit vertikaler Linie und Commit-Punkten
- Material Design 3 Icons statt Emojis

🎨 UI/UX-VERBESSERUNGEN:
- Smooth Accordion-Animation beim Expand/Collapse
- Expand-Icon rotiert beim Öffnen
- Details-Section mit grauem Hintergrund

🔧 TECHNISCHE DETAILS:
- Template: app/templates/md3/admin/changelog.html
- JavaScript: toggleDetails() Funktion
- CSS: Material Design 3 Token-basiert
```

### **Fix-Commit:**
```
🔧 Fix: CSRF-Token-Fehler beim Changelog-Update behoben

📋 PROBLEM:
- CSRF-Token fehlte in Changelog-Formularen
- Server wies POST-Requests mit "CSRF token missing" ab

🎨 LÖSUNG:
- CSRF-Token zu allen Formularen hinzugefügt
- Sowohl MD3 als auch Classic Templates aktualisiert

🔧 TECHNISCHE DETAILS:
- Templates: changelog.html, md3/admin/changelog.html
- Hinzugefügt: <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### **Mobile-Commit:**
```
📱 Mobile: Ausleihen-Seiten optimiert mit Card-Layout (Aktive + Historie)

📋 HAUPTFEATURES:
- Card-Layout statt Tabelle für mobile Geräte
- Asset-Bild prominent in Card-Header
- Grid-Details für bessere Übersicht

🎨 UI/UX-VERBESSERUNGEN:
- Touch-friendly Card-Spacing
- Große Action-Buttons
- Übersichtliche Detail-Grid

📱 MOBILE-OPTIMIERUNG:
- @media (max-width: 768px) Queries
- Tabelle auf Desktop, Cards auf Mobile
- Responsive Bilder und Icons
```

---

## 💡 Best Practices

### **DO:**
✅ Verwende präzise, beschreibende Titel
✅ Liste alle wichtigen Änderungen auf
✅ Erwähne betroffene Dateien/Templates
✅ Beschreibe technische Details
✅ Erkläre UI/UX-Verbesserungen
✅ Dokumentiere Mobile-Optimierungen

### **DON'T:**
❌ Vage Beschreibungen ("Fixed stuff", "Updated UI")
❌ Fehlende technische Details
❌ Keine Emoji-Kategorisierung
❌ Mehrere unabhängige Features in einem Commit
❌ Fehlende Kontext-Informationen

---

## 🎯 Verwendung

### **1. Commit mit Template-Datei:**
```bash
# 1. COMMIT_MSG.txt mit Inhalt erstellen
# 2. Commit mit Datei:
git commit -F COMMIT_MSG.txt
```

### **2. Direkter Commit (kurze Messages):**
```bash
git commit -m "✨ Feature: Kurzbeschreibung"
```

### **3. Multi-Line Commit:**
```bash
git commit -m "✨ Feature: Titel" -m "" -m "📋 DETAILS:" -m "- Detail 1"
```

---

## 📚 Referenz

Diese Vorlage basiert auf:
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Gitmoji**: https://gitmoji.dev/
- **Material Design 3**: https://m3.material.io/

---

**Erstellt am:** 07.10.2025  
**Für:** Asset Management System  
**Von:** Cascade AI Assistant
