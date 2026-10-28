const ownImage = src => typeof src === 'string' && /^\/web\/[a-zA-Z0-9_./-]+\.(?:png|jpg)$/.test(src) && !src.includes('..');

export function playerPhoto(sport, id) {
  return ['nba', 'futbol'].includes(sport) && /^[1-9][0-9]{0,7}$/.test(String(id))
    ? `/web/imagenes/jugadores/${sport}/${id}.png` : null;
}

export function imageMarkup(src, name, esc, css = 'player-photo') {
  const initials = String(name || '?').split(/\s+/).filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase();
  return ownImage(src)
    ? `<img class="${css}" src="${esc(src)}" alt="" data-image-name="${esc(name)}" loading="lazy" decoding="async">`
    : `<span class="${css} is-initial" role="img" aria-label="${esc(`Foto no disponible: ${name}`)}" title="${esc(`Foto no disponible: ${name}`)}">${esc(initials)}</span>`;
}

export function installImageFallback(root) {
  root.addEventListener('error', event => {
    const img = event.target;
    if (img.tagName !== 'IMG' || !img.matches('.player-photo, .win-crest, .crest, .large-crest, .win-pk-avatar img')) return;
    const name = img.dataset.imageName || img.closest('.win-pk-side')?.querySelector('strong')?.textContent || 'Imagen';
    const span = img.ownerDocument.createElement('span');
    span.className = `${img.className} is-initial`;
    span.textContent = name.split(/\s+/).filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase();
    span.title = `Imagen no disponible: ${name}`;
    span.setAttribute('role', 'img');
    span.setAttribute('aria-label', span.title);
    img.replaceWith(span);
  }, true);
}
