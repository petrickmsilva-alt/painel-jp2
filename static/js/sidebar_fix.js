document.addEventListener("DOMContentLoaded", function() {
    let btn = document.createElement("button");
    btn.innerHTML = '<i class="bi bi-list"></i> Menu';
    btn.className = "btn btn-sm btn-dark";
    btn.style.position = "fixed";
    btn.style.top = "15px";
    btn.style.left = "310px";
    btn.style.zIndex = "9999";
    document.body.appendChild(btn);

    // Ajustamos para forçar a largura total quando oculto
    let style = document.createElement('style');
    style.innerHTML = `
        .sidebar-enterprise.hidden { display: none !important; }
        .main-workspace.expanded { margin-left: 0 !important; width: 100% !important; flex-grow: 1 !important; }
        .workspace-wrapper { display: flex !important; width: 100% !important; }
    `;
    document.head.appendChild(style);

    btn.onclick = function() {
        let sidebar = document.querySelector('.sidebar-enterprise');
        let main = document.querySelector('.main-workspace');
        
        if (sidebar && main) {
            sidebar.classList.toggle('hidden');
            main.classList.toggle('expanded');
        }
    };
});