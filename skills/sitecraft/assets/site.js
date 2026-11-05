/* Accessible local controls: no requests, account data or persistent form storage. */
(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const menu = document.querySelector('#site-menu');
  const contact = document.querySelector('#contact-dialog');
  const opener = document.querySelector('[data-open-menu]');
  let closing;
  function open(dialog) {
    if (!dialog || dialog.open) return;
    clearTimeout(closing);
    dialog.removeAttribute('data-closing');
    dialog.showModal();
    document.body.classList.add('is-modal-open');
    if (dialog === menu) opener?.setAttribute('aria-expanded', 'true');
  }
  function close(dialog) {
    if (!dialog?.open || dialog.hasAttribute('data-closing')) return;
    const finish = () => { dialog.close(); dialog.removeAttribute('data-closing'); };
    if (reduced.matches) finish();
    else { dialog.setAttribute('data-closing', ''); closing = setTimeout(finish, 180); }
  }
  opener?.addEventListener('click', () => open(menu));
  document.querySelectorAll('[data-open-contact]').forEach(button => button.addEventListener('click', () => open(contact)));
  document.querySelectorAll('dialog').forEach(dialog => {
    dialog.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => close(dialog)));
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(dialog); });
    dialog.addEventListener('close', () => {
      dialog.removeAttribute('data-closing');
      if (!document.querySelector('dialog[open]')) document.body.classList.remove('is-modal-open');
      if (dialog === menu) opener?.setAttribute('aria-expanded', 'false');
    });
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) close(dialog);
    });
  });
  menu?.querySelectorAll('a').forEach(anchor => anchor.addEventListener('click', () => menu.close()));
  document.querySelector('#contact-form')?.addEventListener('submit', event => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    document.querySelector('#contact-result').textContent = `${String(data.get('name')).trim()}，你的留言预览：\n${String(data.get('message')).trim()}\n\n本地演示已完成，留言未发送、未保存。`;
  });
  document.querySelectorAll('[data-workspace]').forEach(workspace => {
    const detail = workspace.querySelector('.workspace-detail');
    workspace.querySelectorAll('[data-work-item]').forEach(button => button.addEventListener('click', () => {
      workspace.querySelectorAll('[data-work-item]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      detail.querySelector('h3').textContent = button.dataset.title;
      detail.querySelector('.workspace-body').textContent = button.dataset.body;
      detail.getAnimations().forEach(animation => animation.cancel());
      if (!reduced.matches) detail.animate([{opacity:.45,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:220,easing:'cubic-bezier(.2,.7,.25,1)'});
    }));
    if ('IntersectionObserver' in window) new IntersectionObserver(entries => {
      workspace.classList.toggle('is-offscreen', !entries[0].isIntersecting);
    }).observe(workspace);
  });
})();
