(() => {
  'use strict';
  const services = {
    dog: [
      { name: '洗个香香澡', description: '温和清洁、细致吹干，再梳一个蓬松好心情。', time: '约 60–90 分钟', price: '89', icon: 'bubble' },
      { name: '换个可爱造型', description: '从脸颊到小爪子，修出适合它的精神模样。', time: '约 120–180 分钟', price: '169', icon: 'scissors' },
      { name: '毛茸茸养护课', description: '细心梳理与去浮毛，让每一次摸摸都更舒服。', time: '约 90–120 分钟', price: '129', icon: 'comb' }
    ],
    cat: [
      { name: '猫咪温柔净洗', description: '留出适应的时间，慢慢洗，细心吹。', time: '约 90–120 分钟', price: '129', icon: 'bubble' },
      { name: '轻盈去浮毛', description: '顺着毛发生长的方向，梳掉多余小烦恼。', time: '约 90–150 分钟', price: '169', icon: 'comb' },
      { name: '长毛细致梳理', description: '耐心照顾长长的毛发，恢复顺顺软软的模样。', time: '约 120–180 分钟', price: '199', icon: 'comb' }
    ]
  };
  let currentPet = 'dog';
  const tabs = [...document.querySelectorAll('[data-pet]')];
  const panel = document.getElementById('service-list');
  function switchPet(pet) {
    currentPet = pet;
    tabs.forEach(tab => {
      const active = tab.dataset.pet === pet;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panel.setAttribute('aria-labelledby', `${pet}-tab`);
    services[pet].forEach((service, i) => {
      const row = panel.children[i];
      row.querySelector('h3').textContent = service.name;
      row.querySelector('.service-info p').textContent = service.description;
      row.querySelector('.service-time').textContent = service.time;
      row.querySelector('.service-price strong').textContent = service.price;
      row.querySelector('use').setAttribute('href', `#${service.icon}`);
      const button = row.querySelector('button');
      button.dataset.service = service.name;
      button.setAttribute('aria-label', `预约${service.name}`);
    });
  }
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => switchPet(tab.dataset.pet));
    tab.addEventListener('keydown', e => {
      let target;
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') target = tabs[1 - i];
      if (e.key === 'Home') target = tabs[0];
      if (e.key === 'End') target = tabs[1];
      if (target) { e.preventDefault(); switchPet(target.dataset.pet); target.focus(); }
    });
  });
  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('main-nav');
  const closeMenu = () => { nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', '打开导航'); };
  menu.addEventListener('click', () => {
    const open = !nav.classList.contains('open');
    nav.classList.toggle('open', open);
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? '关闭导航' : '打开导航');
  });
  nav.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
  window.matchMedia('(min-width: 701px)').addEventListener('change', closeMenu);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
  const dialog = document.getElementById('booking-dialog');
  const form = document.getElementById('booking-form');
  const select = document.getElementById('booking-service');
  const content = document.getElementById('booking-content');
  const result = document.getElementById('booking-result');
  let lastTrigger;
  function setFormPet(pet, selectedService) {
    select.replaceChildren(...services[pet].map(service => new Option(service.name, service.name)));
    if (selectedService && services[pet].some(s => s.name === selectedService)) select.value = selectedService;
  }
  document.querySelectorAll('[data-book]').forEach(button => button.addEventListener('click', () => {
    lastTrigger = button;
    closeMenu();
    form.reset();
    form.elements.pet.value = currentPet;
    setFormPet(currentPet, button.dataset.service);
    content.hidden = false;
    result.hidden = true;
    dialog.setAttribute('aria-labelledby', 'dialog-title');
    dialog.showModal();
    document.body.classList.add('dialog-open');
  }));
  form.elements.pet.forEach(radio => radio.addEventListener('change', () => setFormPet(radio.value)));
  form.addEventListener('submit', e => {
    e.preventDefault();
    const data = new FormData(form);
    document.getElementById('result-summary').textContent = `${data.get('pet') === 'cat' ? '猫咪' : '狗狗'} · ${data.get('service')}\n${data.get('time')}`;
    content.hidden = true;
    result.hidden = false;
    result.querySelector('h2').id = 'result-title';
    dialog.setAttribute('aria-labelledby', 'result-title');
    dialog.scrollTop = 0;
    result.querySelector('button').focus();
  });
  document.querySelectorAll('.close-dialog,.result-close').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', e => {
    if (e.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('dialog-open');
    lastTrigger?.focus({ preventScroll: true });
  });
})();
