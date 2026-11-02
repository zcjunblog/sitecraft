export function createMotion(reduced) {
  const active = new Map();
  const ghosts = new Map();
  const ease = 'cubic-bezier(.22,.8,.22,1)';
  
  const cancel = el => { const a = active.get(el); if (a) { a.cancel(); active.delete(el); } };
  function animate(el, frames, options = {}) {
    cancel(el);
    if (reduced.matches || !el.animate) return Promise.resolve();
    const a = el.animate(frames, {duration: 480, easing: ease, ...options});
    active.set(el, a);
    return a.finished.catch(() => {}).finally(() => { if (active.get(el) === a) active.delete(el); });
  }
  function clearGhosts(container) {
    const list = ghosts.get(container) || [];
    list.forEach(({node}) => { cancel(node); node.remove(); });
    ghosts.delete(container);
  }
  function layout(container, items, mutate, local = false) {
    const first = new Map();
    items.forEach(el => {
      if (!el.hidden) first.set(el, {rect:el.getBoundingClientRect(), opacity:getComputedStyle(el).opacity});
    });
    (ghosts.get(container)||[]).forEach(({source,node})=>{
      if (node.isConnected&&!first.has(source)) first.set(source,{rect:node.getBoundingClientRect(),opacity:getComputedStyle(node).opacity});
    });
    const from = container.getBoundingClientRect();
    cancel(container); items.forEach(cancel); clearGhosts(container);
    mutate();
    if (reduced.matches) return Promise.resolve();
    const to = container.getBoundingClientRect(), exiting = [], jobs = [];
    const delay=items.some(el=>el.hidden&&first.has(el))?120:0;
    items.forEach(el => {
      const old = first.get(el);
      if (el.hidden) {
        if (!old) return;
        const clone = el.cloneNode(true);
        clone.hidden = false; clone.inert = true; clone.setAttribute('aria-hidden','true');
        for (const node of [clone,...clone.querySelectorAll('*')]) {
          node.removeAttribute('id');
          for (const attr of [...node.attributes]) if(attr.name.startsWith('data-')) node.removeAttribute(attr.name);
        }
        clone.classList.add('motion-ghost');
        Object.assign(clone.style,{position:local?'absolute':'fixed',margin:'0',left:`${old.rect.left-(local?from.left:0)}px`,top:`${old.rect.top-(local?from.top:0)}px`,width:`${old.rect.width}px`,height:`${old.rect.height}px`,pointerEvents:'none',zIndex:'8'});
        (local?container:document.body).append(clone);
        exiting.push({source:el,node:clone});
        jobs.push(animate(clone,[{opacity:old.opacity,transform:'translateY(0) scale(1)'},{opacity:0,transform:'translateY(-14px) scale(.985)'}],{duration:110}).then(()=>clone.remove()));
      } else {
        const end = el.getBoundingClientRect();
        const dx = old?old.rect.left-end.left:0, dy=old?old.rect.top-end.top:22;
        jobs.push(animate(el,[{transform:`translate(${dx}px,${dy}px)`,opacity:old?old.opacity:0},{transform:'translate(0,0)',opacity:1}],{duration:440,delay,fill:'backwards'}));
      }
    });
    ghosts.set(container,exiting);
    if(Math.abs(from.height-to.height)>1) jobs.push(animate(container,[{height:`${from.height}px`},{height:`${to.height}px`}],{duration:440,delay,fill:'backwards'}));
    const owned=exiting;
    return Promise.all(jobs).then(()=>{if(ghosts.get(container)===owned)clearGhosts(container);});
  }
  reduced.addEventListener('change',()=>{for(const el of [...active.keys()])cancel(el);for(const container of [...ghosts.keys()])clearGhosts(container);});
  return {animate,cancel,layout};
}
