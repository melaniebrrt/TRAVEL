document.addEventListener('DOMContentLoaded', () => {

  // ===================
  // CARTE
  // ===================
  const map = L.map('map').setView([46.603354, 1.888334], 6);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const markersLayer = L.layerGroup().addTo(map);

  // ===================
  // DOM
  // ===================
  const interestSelect = document.getElementById('interest-select');
  const searchInput = document.getElementById('search-input');
  const searchButton = document.getElementById('search-button');
  const eventListContainer = document.getElementById('event-list-container');
  const cityResultsContainer = document.getElementById('city-results-container');
  const dateStartInput = document.getElementById('date-start');
  const dateEndInput = document.getElementById('date-end');
  const sortButton = document.getElementById('sort-date-button');
  const darkToggle = document.getElementById('dark-toggle');

  let sortByDate = false;
  let selectedCity = null;

  // ===================
  // MODE SOMBRE
  // ===================
  darkToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark');
    darkToggle.textContent = document.body.classList.contains('dark')
      ? 'Mode clair ☀️'
      : 'Mode sombre 🌙';
  });

  // ===================
  // TRI PAR DATE
  // ===================
  sortButton.addEventListener('click', () => {
    sortByDate = !sortByDate;
    sortButton.textContent = sortByDate ? 'Trier : Date ↑' : 'Trier';
    searchEvents();
  });

  // ===================
  // CATÉGORIES
  // ===================
  fetch('/api/categories')
    .then(res => res.json())
    .then(categories => {
      interestSelect.innerHTML = '';
      categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        interestSelect.appendChild(option);
      });
    });

  // ===================
  // EVENT CARD
  // ===================
  function createEventCard(e) {
    const card = document.createElement('div');
    card.className = 'event-card';

    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerHTML = `
      <div class="small">
        ${e.DateTime_start
          ? new Date(e.DateTime_start).toLocaleDateString('fr-FR')
          : 'N/A'}
      </div>
      <div class="small">${e.City || 'N/A'}</div>
    `;

    const body = document.createElement('div');
    body.style.flex = '1';

    const title = document.createElement('h3');
    title.textContent = e.EventName || 'Sans titre';

    const desc = document.createElement('p');
    desc.textContent = e.Description
      ? (e.Description.length > 180
          ? e.Description.slice(0, 180) + '…'
          : e.Description)
      : 'Pas de description.';

    const tags = document.createElement('div');
    tags.className = 'tags';

    if (e.Category) {
      const tag = document.createElement('span');
      tag.className = 'tag';
      tag.textContent = e.Category;
      tags.appendChild(tag);
    }

    const link = document.createElement('a');
    link.href = e.Link || '#';
    link.target = '_blank';
    link.className = 'small';
    link.textContent = 'Voir la source ↗';

    body.append(title, desc, tags, link);
    card.append(meta, body);

    return card;
  }

  // ===================
  // QUERY PARAMS
  // ===================
  function buildQueryParams(includeCity = true) {
    const params = new URLSearchParams();

    const selectedOptions = Array.from(interestSelect.selectedOptions)
      .map(opt =>
        opt.value
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '')
          .toLowerCase()
      );

    if (selectedOptions.length) {
      const weighted = selectedOptions.map(i => `${i}:2`);
      params.set('interests', weighted.join(','));
    }

    params.set('q', searchInput.value.trim() || '');

    if (dateStartInput.value) params.set('start_date', dateStartInput.value);
    if (dateEndInput.value) params.set('end_date', dateEndInput.value);
    if (sortByDate) params.set('sort', 'date');

    if (includeCity && selectedCity) {
      params.set('city', selectedCity);
    }

    return params.toString();
  }

  // ===================
  // RECHERCHE
  // ===================
  function searchEvents() {

    cityResultsContainer.innerHTML = '<div class="small">Chargement…</div>';
    fetchCities(buildQueryParams(false));

    const url = `/api/smart-search?${buildQueryParams(true)}`;
    eventListContainer.innerHTML = '<div class="small">Chargement…</div>';
    markersLayer.clearLayers();

    fetch(url)
      .then(res => res.json())
      .then(events => {
        eventListContainer.innerHTML = '';

        if (!events || !events.length) {
          eventListContainer.innerHTML =
            '<div class="small">Aucun événement trouvé.</div>';
          return;
        }

        events.slice(0, 60).forEach(ev => {
          eventListContainer.appendChild(createEventCard(ev));

          if (ev.lat && ev.lon) {
            const marker = L.marker([ev.lat, ev.lon]).addTo(markersLayer);
            marker.bindPopup(`
              <strong>${ev.EventName}</strong><br>
              ${ev.City || ''}<br>
              ${ev.Category || ''}
            `);
          }
        });

        if (markersLayer.getLayers().length) {
          map.fitBounds(markersLayer.getBounds().pad(0.15));
        }
      });
  }

  // ===================
  // VILLES
  // ===================
  function fetchCities(queryString) {
    fetch(`/api/cities-by-llm?${queryString}`)
      .then(res => res.json())
      .then(renderCities)
      .catch(() => {
        cityResultsContainer.innerHTML = '<div class="small">-</div>';
      });
  }

  function renderCities(cities) {
    cityResultsContainer.innerHTML = '';

    if (!cities || !cities.length) {
      cityResultsContainer.innerHTML = '<div class="small">-</div>';
      return;
    }

    cities.slice(0, 8).forEach(c => {
      const div = document.createElement('div');
      div.className = 'city-pill';
      div.style.cursor = 'pointer';

      if (selectedCity === c.City) {
        div.classList.add('active');
      }

      div.innerHTML = `
        <span>${c.City}</span>
        <span class="small">${c.count}</span>
      `;

      div.addEventListener('click', () => {
        selectedCity = c.City;
        searchEvents();
      });

      cityResultsContainer.appendChild(div);
    });
  }

  // ===================
  // UI
  // ===================
  searchButton.addEventListener('click', searchEvents);

  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') searchEvents();
  });

  interestSelect.addEventListener('change', () => {
    selectedCity = null;
    searchEvents();
  });

  dateStartInput.addEventListener('change', () => {
    selectedCity = null;
    searchEvents();
  });

  dateEndInput.addEventListener('change', () => {
    selectedCity = null;
    searchEvents();
  });

  feather.replace();

  // ===================
  // CHARGEMENT INITIAL
  // ===================
  searchEvents();
});
