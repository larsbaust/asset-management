/**
 * MD3 Calendar JavaScript
 * Ermöglicht Monatsnavigation, Datumsauswahl und Ripple-Effekte
 */

document.addEventListener('DOMContentLoaded', function() {
  // Aktuelles Datum und Kalender-Zustand
  let currentDate = new Date();
  let currentYear = currentDate.getFullYear();
  let currentMonth = currentDate.getMonth();
  
  // Element-Referenzen
  const calendarTitle = document.querySelector('.md3-calendar-title');
  const prevMonthBtn = document.getElementById('prev-month-btn');
  const nextMonthBtn = document.getElementById('next-month-btn');
  const todayBtn = document.getElementById('today-btn');
  const calendarGrid = document.querySelector('.md3-calendar-grid');
  
  // Monatsnamen
  const monthNames = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                      'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
  
  // Monatskalender rendern
  function renderCalendar(year, month) {
    // Titel aktualisieren
    calendarTitle.textContent = `${monthNames[month]} ${year}`;
    
    // Kalendertage berechnen
    const firstDay = new Date(year, month, 1).getDay(); // 0 = Sonntag, 1 = Montag, ...
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const lastMonth = month === 0 ? 11 : month - 1;
    const lastMonthYear = month === 0 ? year - 1 : year;
    const daysInLastMonth = new Date(lastMonthYear, lastMonth + 1, 0).getDate();
    
    // Wochentag anpassen (0 = Sonntag → 6, 1 = Montag → 0, ...)
    let startDay = firstDay === 0 ? 6 : firstDay - 1;
    
    // Alle Tages-Elemente aus dem Grid entfernen, aber Wochentage behalten
    const dayElements = calendarGrid.querySelectorAll('.md3-calendar-day');
    dayElements.forEach(day => day.remove());
    
    // Tage des vorherigen Monats
    for (let i = 0; i < startDay; i++) {
      const dayNum = daysInLastMonth - startDay + i + 1;
      const dayEl = createDayElement(dayNum, 'other-month');
      calendarGrid.appendChild(dayEl);
    }
    
    // Tage des aktuellen Monats
    const today = new Date();
    const isCurrentMonth = today.getMonth() === month && today.getFullYear() === year;
    const todayDate = today.getDate();
    
    for (let i = 1; i <= daysInMonth; i++) {
      const isToday = isCurrentMonth && i === todayDate;
      const dayEl = createDayElement(i, isToday ? 'today' : '');
      calendarGrid.appendChild(dayEl);
    }
    
    // Tage des nächsten Monats (bis Grid vollständig ist)
    const totalDays = startDay + daysInMonth;
    const nextMonthDays = totalDays % 7 === 0 ? 0 : 7 - (totalDays % 7);
    
    for (let i = 1; i <= nextMonthDays; i++) {
      const dayEl = createDayElement(i, 'other-month');
      calendarGrid.appendChild(dayEl);
    }
    
    // Wenn der Monat weniger als 6 Wochen hat, füge eine zusätzliche Zeile hinzu
    const totalRows = Math.ceil((startDay + daysInMonth) / 7);
    if (totalRows < 6) {
      for (let i = 1; i <= 7; i++) {
        const dayNum = nextMonthDays + i;
        const dayEl = createDayElement(dayNum, 'other-month');
        calendarGrid.appendChild(dayEl);
      }
    }
  }
  
  // Hilfsfunktion zum Erstellen eines Tages-Elements
  function createDayElement(day, className = '') {
    const dayEl = document.createElement('div');
    dayEl.className = `md3-calendar-day ${className}`;
    dayEl.textContent = day;
    
    // Inline-Styles für konsistentes Rendering
    dayEl.style.padding = '8px';
    dayEl.style.textAlign = 'center';
    dayEl.style.borderRadius = '4px';
    dayEl.style.minHeight = '40px';
    dayEl.style.display = 'flex';
    dayEl.style.alignItems = 'center';
    dayEl.style.justifyContent = 'center';
    dayEl.style.cursor = 'pointer';
    
    // Spezielle Stile für verschiedene Zustände
    if (className.includes('today')) {
      dayEl.style.color = 'var(--md-sys-color-primary, #6750a4)';
      dayEl.style.fontWeight = '700';
      dayEl.style.border = '1px solid var(--md-sys-color-primary, #6750a4)';
    } else if (className.includes('other-month')) {
      dayEl.style.color = 'var(--md-sys-color-outline, #79747e)';
      dayEl.style.opacity = '0.6';
    }
    
    // Click-Handler für Tagesauswahl
    dayEl.addEventListener('click', function() {
      // Aktive Klasse von allen Tagen entfernen
      document.querySelectorAll('.md3-calendar-day.active').forEach(el => {
        el.classList.remove('active');
        el.style.backgroundColor = '';
        el.style.color = el.classList.contains('other-month') ? 'var(--md-sys-color-outline, #79747e)' : '';
      });
      
      // Aktiven Zustand für diesen Tag setzen
      this.classList.add('active');
      this.style.backgroundColor = 'var(--md-sys-color-primary, #6750a4)';
      this.style.color = 'var(--md-sys-color-on-primary, #ffffff)';
      
      // Datum auswählen (hier könnte ein Event oder Callback erfolgen)
      const selectedMonth = this.classList.contains('other-month') ? 
        (this.textContent < 15 ? currentMonth + 1 : currentMonth - 1) : currentMonth;
      const selectedYear = selectedMonth === 12 ? currentYear + 1 : (selectedMonth === -1 ? currentYear - 1 : currentYear);
      const selectedDate = new Date(selectedYear, selectedMonth === 12 ? 0 : (selectedMonth === -1 ? 11 : selectedMonth), parseInt(this.textContent));
      
      console.log('Selected date:', selectedDate.toLocaleDateString());
      // Hier könnte man einen Event-Listener hinzufügen oder eine Callback-Funktion aufrufen
    });
    
    return dayEl;
  }
  
  // Event-Handler
  prevMonthBtn.addEventListener('click', function() {
    currentMonth--;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear--;
    }
    renderCalendar(currentYear, currentMonth);
  });
  
  nextMonthBtn.addEventListener('click', function() {
    currentMonth++;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear++;
    }
    renderCalendar(currentYear, currentMonth);
  });
  
  todayBtn.addEventListener('click', function() {
    const today = new Date();
    currentYear = today.getFullYear();
    currentMonth = today.getMonth();
    renderCalendar(currentYear, currentMonth);
  });
  
  // Ripple-Effekt für MD3-Buttons
  function addRippleEffect(element) {
    element.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.classList.add('ripple');
      this.appendChild(ripple);
      
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left - size/2}px`;
      ripple.style.top = `${e.clientY - rect.top - size/2}px`;
      
      ripple.classList.add('active');
      
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  }
  
  // Ripple-Effekt zu allen Buttons hinzufügen
  document.querySelectorAll('.md3-calendar-prev, .md3-calendar-today, .md3-calendar-next').forEach(addRippleEffect);
  
  // Tastatur-Navigation
  document.addEventListener('keydown', function(e) {
    if (document.activeElement && document.activeElement.classList.contains('md3-calendar-day')) {
      const activeDay = document.activeElement;
      const days = Array.from(document.querySelectorAll('.md3-calendar-day'));
      const currentIndex = days.indexOf(activeDay);
      
      switch(e.key) {
        case 'ArrowRight':
          if (currentIndex < days.length - 1) {
            days[currentIndex + 1].focus();
          }
          break;
        case 'ArrowLeft':
          if (currentIndex > 0) {
            days[currentIndex - 1].focus();
          }
          break;
        case 'ArrowUp':
          if (currentIndex >= 7) {
            days[currentIndex - 7].focus();
          }
          break;
        case 'ArrowDown':
          if (currentIndex < days.length - 7) {
            days[currentIndex + 7].focus();
          }
          break;
        case 'Enter':
        case ' ':
          activeDay.click();
          break;
      }
    }
  });
  
  // Initial rendern
  renderCalendar(currentYear, currentMonth);
});
