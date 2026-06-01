document.addEventListener("DOMContentLoaded", () => {
    const fileTree = document.getElementById("file-tree");
    const tabsContainer = document.getElementById('editor-tabs-container');
    const btnSaveFile = document.getElementById("btn-save-file");
    const btnRefreshFs = document.getElementById("btn-refresh-fs");
    
    let currentFilePath = null;
    let editor = null;
    let openTabs = []; // Array of { path, name, model }

    // Initialize Monaco Editor
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.43.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {
        document.getElementById('editor-loading').style.display = 'none';
        
        // Load saved IDE settings
        const ideSettings = JSON.parse(localStorage.getItem('alas_ide_settings')) || { theme: 'vs-dark', fontSize: 14, wordWrap: 'off' };
        
        editor = monaco.editor.create(document.getElementById('code-editor-container'), {
            value: "// Select a file from the explorer to begin editing...",
            language: "javascript",
            theme: ideSettings.theme,
            fontSize: ideSettings.fontSize,
            wordWrap: ideSettings.wordWrap,
            automaticLayout: true,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            roundedSelection: false,
            padding: { top: 16 }
        });
        
        // Add save shortcut to Monaco
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, function() {
            saveFile();
        });
    });

    function getLanguageFromExtension(path) {
        const ext = path.split('.').pop().toLowerCase();
        const map = {
            'js': 'javascript', 'ts': 'typescript', 'py': 'python',
            'html': 'html', 'css': 'css', 'json': 'json',
            'md': 'markdown', 'sh': 'shell', 'bash': 'shell',
            'yml': 'yaml', 'yaml': 'yaml', 'xml': 'xml', 'sql': 'sql',
            'cpp': 'cpp', 'c': 'c', 'h': 'cpp', 'java': 'java', 'go': 'go', 'rs': 'rust'
        };
        return map[ext] || 'plaintext';
    }

    async function loadFolder(path, containerEl, indentLevel = 0) {
        try {
            const response = await fetch(`/api/fs/list?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error("Failed to load");
            const data = await response.json();
            
            containerEl.innerHTML = ''; 
            
            data.items.forEach(item => {
                const el = document.createElement("div");
                
                const header = document.createElement("div");
                header.className = "file-item";
                header.style.paddingLeft = `${16 + indentLevel * 12}px`;
                
                let icon = item.is_dir ? '▶' : '📄'; 
                if (item.is_dir) icon = `<span class="chevron" style="display:inline-block; transition:transform 0.1s; width:16px; font-size:0.7rem; color:var(--text-muted);">▶</span>`;
                else {
                    const lName = item.name.toLowerCase();
                    let eIcon = '📄';
                    if (lName.endsWith('.py')) eIcon = '🐍';
                    else if (lName.endsWith('.js') || lName.endsWith('.ts')) eIcon = '📜';
                    else if (lName.endsWith('.json')) eIcon = '🔧';
                    else if (lName.endsWith('.pdf')) eIcon = '📕';
                    else if (lName.endsWith('.md')) eIcon = '📖';
                    else if (lName.endsWith('.html')) eIcon = '🌐';
                    else if (lName.endsWith('.css')) eIcon = '🎨';
                    else if (lName.endsWith('.png') || lName.endsWith('.jpg') || lName.endsWith('.svg')) eIcon = '🖼️';
                    icon = `<span style="font-size:0.9rem; filter:grayscale(0.2); width:20px; text-align:center;">${eIcon}</span>`;
                }

                header.innerHTML = `${icon} <span>${item.name}</span>`;
                el.appendChild(header);
                
                if (item.is_dir) {
                    const childrenContainer = document.createElement("div");
                    childrenContainer.style.display = "none";
                    el.appendChild(childrenContainer);
                    
                    let isOpen = false;
                    header.onclick = () => {
                        isOpen = !isOpen;
                        const chevron = header.querySelector('.chevron');
                        if (isOpen) {
                            chevron.style.transform = "rotate(90deg)";
                            childrenContainer.style.display = "block";
                            if (childrenContainer.innerHTML === "") {
                                childrenContainer.innerHTML = `<div class="file-item" style="padding-left:${16 + (indentLevel+1)*12}px; color:var(--text-muted); font-size:0.75rem;">Loading...</div>`;
                                loadFolder(item.path, childrenContainer, indentLevel + 1);
                            }
                        } else {
                            chevron.style.transform = "rotate(0deg)";
                            childrenContainer.style.display = "none";
                        }
                    };
                } else {
                    header.onclick = () => {
                        loadFile(item.path);
                        document.querySelectorAll('.file-item').forEach(i => i.classList.remove('active'));
                        header.classList.add('active');
                    };
                }
                containerEl.appendChild(el);
            });
        } catch(e) {
            containerEl.innerHTML = `<div class="file-item" style="color:var(--danger);">Error loading folder</div>`;
        }
    }

    function initFileTree() {
        fileTree.innerHTML = '<div style="padding:10px;text-align:center;color:#64748b;">Loading...</div>';
        loadFolder("", fileTree, 0);
    }

    function renderTabs() {
        tabsContainer.innerHTML = '';
        if (openTabs.length === 0) {
            tabsContainer.innerHTML = '<div class="editor-tab active">Welcome to ALAS IDE</div>';
            if (editor) editor.setModel(null);
            document.getElementById('code-editor-container').style.display = 'block';
            document.getElementById('pdf-viewer-container').style.display = 'none';
            document.getElementById('ext-viewer-container').style.display = 'none';
            currentFilePath = null;
            return;
        }
        
        openTabs.forEach(tab => {
            const el = document.createElement('div');
            el.className = 'editor-tab' + (tab.path === currentFilePath ? ' active' : '');
            el.style.cursor = 'pointer';
            el.innerHTML = `<span>${tab.name}</span> <button class="tab-close" style="background:none; border:none; margin-left:8px; cursor:pointer; color:inherit; font-size:1rem; opacity:0.6;">×</button>`;
            
            el.querySelector('span').onclick = () => {
                switchTab(tab);
            };
            
            el.querySelector('.tab-close').onmouseover = (e) => e.target.style.opacity = '1';
            el.querySelector('.tab-close').onmouseout = (e) => e.target.style.opacity = '0.6';
            el.querySelector('.tab-close').onclick = (e) => {
                e.stopPropagation();
                closeTab(tab.path);
            };
            
            tabsContainer.appendChild(el);
        });
    }

    function switchTab(tab) {
        currentFilePath = tab.path;
        
        document.getElementById('code-editor-container').style.display = 'none';
        document.getElementById('pdf-viewer-container').style.display = 'none';
        document.getElementById('ext-viewer-container').style.display = 'none';

        if (tab.isPdf) {
            document.getElementById('pdf-viewer-container').style.display = 'block';
            document.getElementById('pdf-iframe').src = `/api/fs/raw?path=${encodeURIComponent(tab.path)}`;
        } else if (tab.isExt) {
            const extViewer = document.getElementById('ext-viewer-container');
            extViewer.style.display = 'block';
            
            const ext = tab.extData;
            const iconUrl = ext.files && ext.files.icon ? ext.files.icon : 'https://open-vsx.org/default-icon.png';
            const isInstalled = getInstalledExtensions().includes(`${ext.namespace}.${ext.name}`);
            const actionBtnHTML = isInstalled 
                ? `<button id="btn-ext-action-${ext.namespace}-${ext.name}" class="modal-save-btn" style="margin:0; padding: 8px 24px; font-size: 0.95rem; background: var(--bg-tertiary); border: 1px solid var(--border-subtle); color: var(--text-primary);">Uninstall</button>`
                : `<button id="btn-ext-action-${ext.namespace}-${ext.name}" class="modal-save-btn" style="margin:0; padding: 8px 24px; font-size: 0.95rem;">Install Extension</button>`;

            extViewer.innerHTML = `
                <div style="display:flex; gap: 24px; margin-bottom: 30px; align-items: flex-start;">
                    <img src="${iconUrl}" style="width: 120px; height: 120px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                    <div>
                        <h1 style="margin: 0 0 8px 0; font-size: 2.2rem; display: flex; align-items: center; gap: 10px; color: var(--text-primary);">
                            ${ext.displayName || ext.name}
                        </h1>
                        <div style="color: var(--text-muted); font-size: 0.95rem; display: flex; gap: 20px;">
                            <span>🏢 ${ext.publisher ? ext.publisher.displayName : ext.namespace}</span>
                            <span>⭐ ${ext.reviewCount || 0} reviews</span>
                            <span>📥 ${(ext.downloadCount || 0).toLocaleString()} downloads</span>
                            <span>v${ext.version}</span>
                        </div>
                        <p style="margin-top: 16px; font-size: 1.05rem; line-height: 1.5; color: var(--text-secondary); max-width: 800px;">${ext.description}</p>
                        <div style="margin-top: 20px; display:flex; gap:12px;">
                            ${actionBtnHTML}
                        </div>
                    </div>
                </div>
                <div style="border-bottom: 1px solid var(--border-subtle); margin-bottom: 24px;">
                    <div style="padding-bottom: 12px; border-bottom: 2px solid var(--accent-primary); display: inline-block; color: var(--text-primary); font-weight: 600; font-size: 1.1rem;">Details & README</div>
                </div>
                <div id="ext-readme-${ext.namespace}-${ext.name}" class="markdown-body" style="line-height: 1.8; color: var(--text-secondary); font-size: 0.95rem;">
                    Loading documentation from registry...
                </div>
            `;

            const actionBtn = document.getElementById(`btn-ext-action-${ext.namespace}-${ext.name}`);
            actionBtn.onclick = () => {
                const extId = `${ext.namespace}.${ext.name}`;
                let installed = getInstalledExtensions();
                if (installed.includes(extId)) {
                    actionBtn.textContent = 'Uninstalling...';
                    setTimeout(() => {
                        setInstalledExtensions(installed.filter(id => id !== extId));
                        switchTab(tab); // re-render
                        const extSearchInput = document.getElementById('ext-search-input');
                        if (extSearchInput && extSearchInput.value.trim() === '') renderDefaultExtensionsView();
                    }, 800);
                } else {
                    actionBtn.textContent = 'Installing...';
                    setTimeout(() => {
                        installed.push(extId);
                        setInstalledExtensions(installed);
                        switchTab(tab); // re-render
                        const extSearchInput = document.getElementById('ext-search-input');
                        if (extSearchInput && extSearchInput.value.trim() === '') renderDefaultExtensionsView();
                    }, 1200);
                }
            };
            
            const readmeEl = document.getElementById(`ext-readme-${ext.namespace}-${ext.name}`);
            const readmeUrl = ext.files && ext.files.readme ? ext.files.readme : null;
            if (readmeUrl) {
                fetch(readmeUrl).then(res => res.text()).then(text => {
                    if (window.marked) {
                        readmeEl.innerHTML = marked.parse(text);
                    } else {
                        readmeEl.innerHTML = `<pre style="white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; background: var(--bg-secondary); padding: 20px; border-radius: 8px; border: 1px solid var(--border-subtle); color: var(--text-primary);">${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`;
                    }
                }).catch(() => {
                    readmeEl.innerHTML = "Documentation unavailable.";
                });
            } else {
                readmeEl.innerHTML = "No detailed documentation provided by publisher.";
            }
        } else {
            document.getElementById('code-editor-container').style.display = 'block';
            if (editor) editor.setModel(tab.model);
        }
        
        renderTabs();
    }

    function closeTab(path) {
        const index = openTabs.findIndex(t => t.path === path);
        if (index > -1) {
            if (openTabs[index].model) openTabs[index].model.dispose();
            openTabs.splice(index, 1);
            
            if (currentFilePath === path) {
                if (openTabs.length > 0) {
                    const newTab = openTabs[openTabs.length - 1];
                    switchTab(newTab);
                } else {
                    currentFilePath = null;
                    if (editor) editor.setModel(null);
                    document.getElementById('code-editor-container').style.display = 'block';
                    document.getElementById('pdf-viewer-container').style.display = 'none';
                    renderTabs();
                }
            } else {
                renderTabs();
            }
        }
    }

    async function loadFile(path) {
        try {
            const fileName = path.split('/').pop();
            const isPdf = fileName.toLowerCase().endsWith('.pdf');
            
            // Check if tab already open
            let tab = openTabs.find(t => t.path === path);
            
            if (!tab) {
                tabsContainer.innerHTML = '<div class="editor-tab active">Loading...</div>';
                
                if (isPdf) {
                    tab = { path: path, name: fileName, isPdf: true, model: null };
                } else {
                    const response = await fetch(`/api/fs/read?path=${encodeURIComponent(path)}`);
                    if (!response.ok) throw new Error("Failed to read file");
                    
                    const data = await response.json();
                    const lang = getLanguageFromExtension(path);
                    
                    const model = monaco.editor.createModel(data.content, lang);
                    tab = { path: path, name: fileName, isPdf: false, model: model };
                }
                openTabs.push(tab);
            }
            
            switchTab(tab);
        } catch (e) {
            console.error(e);
            alert(`Error loading file: ${e.message}`);
            renderTabs();
        }
    }

    async function saveFile() {
        if (!currentFilePath || !editor) return;
        
        try {
            btnSaveFile.textContent = "Saving...";
            const response = await fetch(`/api/fs/write?path=${encodeURIComponent(currentFilePath)}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: editor.getValue() })
            });
            
            if (!response.ok) throw new Error("Failed to save file");
            btnSaveFile.textContent = "✅ Saved";
            setTimeout(() => btnSaveFile.textContent = "💾 Save", 2000);
        } catch (e) {
            console.error(e);
            btnSaveFile.textContent = "❌ Error";
            setTimeout(() => btnSaveFile.textContent = "💾 Save", 2000);
        }
    }

    btnSaveFile.addEventListener("click", saveFile);
    btnRefreshFs.addEventListener("click", () => initFileTree());
    
    // Listen for IDE settings update event from app.js
    window.addEventListener('alas_ide_settings_updated', (e) => {
        if (editor) {
            const s = e.detail;
            monaco.editor.setTheme(s.theme);
            editor.updateOptions({ fontSize: s.fontSize, wordWrap: s.wordWrap });
        }
    });

    // Toggle Views (Explorer vs Extensions)
    const btnExplorer = document.getElementById('btn-view-explorer');
    const btnExtensions = document.getElementById('btn-view-extensions');
    const panelExplorer = document.getElementById('ide-explorer');
    const panelExtensions = document.getElementById('ide-extensions');

    if (btnExplorer && btnExtensions) {
        btnExplorer.addEventListener('click', () => {
            btnExtensions.classList.remove('active');
            btnExplorer.classList.add('active');
            panelExtensions.style.display = 'none';
            panelExplorer.style.display = 'flex';
        });

        btnExtensions.addEventListener('click', () => {
            btnExplorer.classList.remove('active');
            btnExtensions.classList.add('active');
            panelExplorer.style.display = 'none';
            panelExtensions.style.display = 'flex';
        });
    }

    // --- Extensions Marketplace Logic ---
    const extSearchInput = document.getElementById('ext-search-input');
    const extResultsContainer = document.getElementById('ext-results-container');
    let extSearchTimeout;
    
    function getInstalledExtensions() {
        const stored = localStorage.getItem('alas_installed_extensions');
        if (stored) return JSON.parse(stored);
        // Default mock list if never set
        const defaults = ['ms-python.python', 'ms-azuretools.vscode-docker', 'golang.go'];
        localStorage.setItem('alas_installed_extensions', JSON.stringify(defaults));
        return defaults;
    }
    
    function setInstalledExtensions(exts) {
        localStorage.setItem('alas_installed_extensions', JSON.stringify(exts));
    }
    
    function renderDefaultExtensionsView() {
        extResultsContainer.innerHTML = `
            <div class="ext-section">
                <div class="ext-section-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                    <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Installed</span>
                </div>
                <div class="ext-section-content" id="ext-installed-list" style="padding-top: 8px;">
                    <div style="padding: 10px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">Loading...</div>
                </div>
            </div>
            <div class="ext-section" style="margin-top: 16px;">
                <div class="ext-section-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                    <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Recommended</span>
                </div>
                <div class="ext-section-content" id="ext-recommended-list" style="padding-top: 8px;">
                    <div style="padding: 10px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">Loading...</div>
                </div>
            </div>
        `;
        
        const installed = getInstalledExtensions();
        fetchDefaultExtensions(installed, 'ext-installed-list');
        // Fetch mock recommended (filtering out already installed ones)
        const recommended = ['esbenp.prettier-vscode', 'dbaeumer.vscode-eslint', 'rust-lang.rust-analyzer'].filter(id => !installed.includes(id));
        if (recommended.length > 0) {
            fetchDefaultExtensions(recommended, 'ext-recommended-list');
        } else {
            document.getElementById('ext-recommended-list').innerHTML = '<div style="padding: 10px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">All recommended extensions installed!</div>';
        }
    }

    async function fetchDefaultExtensions(extList, containerId) {
        try {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            const promises = extList.map(async (id) => {
                const [ns, name] = id.split('.');
                const res = await fetch(`https://open-vsx.org/api/${ns}/${name}`);
                if (!res.ok) return null;
                return await res.json();
            });
            
            const results = (await Promise.all(promises)).filter(r => r !== null);
            container.innerHTML = '';
            
            results.forEach(ext => {
                const card = createExtensionCard(ext);
                container.appendChild(card);
            });
        } catch (e) {
            const c = document.getElementById(containerId);
            if(c) c.innerHTML = '<div style="padding:10px;color:var(--danger);font-size:0.8rem;">Error loading extensions.</div>';
        }
    }

    function createExtensionCard(ext) {
        const card = document.createElement('div');
        card.className = 'extension-card';
        card.style.cursor = 'pointer';
        
        const iconUrl = ext.files && ext.files.icon ? ext.files.icon : 'https://open-vsx.org/default-icon.png';
        const extId = `${ext.namespace}.${ext.name}`;
        const isInstalled = getInstalledExtensions().includes(extId);
        
        card.innerHTML = `
            <div class="ext-icon" style="background-image: url('${iconUrl}'); background-size: cover; background-position:center; border-radius: 4px;"></div>
            <div class="ext-info" style="flex:1; min-width:0;">
                <h4 style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${ext.displayName || ext.name}">${ext.displayName || ext.name}</h4>
                <p style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${ext.description}">${ext.description}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size: 0.65rem; color: var(--text-muted);">${ext.namespace}</span>
                    <button class="ext-btn ${isInstalled ? 'installed' : ''}" onclick="event.stopPropagation(); window.toggleExtension(this, '${extId}', '${ext.namespace}', '${ext.name}')">
                        ${isInstalled ? 'Uninstall' : 'Install'}
                    </button>
                </div>
            </div>
        `;
        
        card.onclick = () => openExtensionDetails(ext.namespace, ext.name, ext);
        return card;
    }
    
    window.toggleExtension = (btn, extId, namespace, name) => {
        let installed = getInstalledExtensions();
        if (installed.includes(extId)) {
            btn.textContent = 'Uninstalling...';
            setTimeout(() => {
                setInstalledExtensions(installed.filter(id => id !== extId));
                btn.textContent = 'Install';
                btn.classList.remove('installed');
                if (extSearchInput && extSearchInput.value.trim() === '') renderDefaultExtensionsView();
                // Also update the active tab if it's the one we are modifying
                const tabId = "ext:" + namespace + "." + name;
                if (currentFilePath === tabId) {
                    const tab = openTabs.find(t => t.path === tabId);
                    if (tab) renderExtensionViewer(tab);
                }
            }, 800);
        } else {
            btn.textContent = 'Installing...';
            setTimeout(() => {
                installed.push(extId);
                setInstalledExtensions(installed);
                btn.textContent = 'Uninstall';
                btn.classList.add('installed');
                if (extSearchInput && extSearchInput.value.trim() === '') renderDefaultExtensionsView();
                // Also update the active tab if it's the one we are modifying
                const tabId = "ext:" + namespace + "." + name;
                if (currentFilePath === tabId) {
                    const tab = openTabs.find(t => t.path === tabId);
                    if (tab) renderExtensionViewer(tab);
                }
            }, 1200);
        }
    };

    async function openExtensionDetails(namespace, name, partialExt) {
        const tabId = "ext:" + namespace + "." + name;
        let tab = openTabs.find(t => t.path === tabId);
        
        if (!tab) {
            tab = {
                path: tabId,
                name: partialExt.displayName || name,
                isExt: true,
                extData: partialExt, // initially partial
                model: null
            };
            openTabs.push(tab);
        }
        
        switchTab(tab);
        
        // Fetch full extension details to get the readme
        try {
            const res = await fetch(`https://open-vsx.org/api/${namespace}/${name}`);
            if (res.ok) {
                const fullExt = await res.json();
                tab.extData = fullExt;
                // re-render if it's the currently viewed tab
                if (currentFilePath === tabId) {
                    switchTab(tab);
                }
            }
        } catch (e) {
            console.error("Failed to fetch full details:", e);
        }
    }

    if (extSearchInput) {
        extSearchInput.addEventListener('input', (e) => {
            clearTimeout(extSearchTimeout);
            extSearchTimeout = setTimeout(() => {
                const query = e.target.value.trim();
                if (query.length > 2) {
                    searchExtensions(query);
                } else if (query.length === 0) {
                    renderDefaultExtensionsView();
                }
            }, 500);
        });
    }

    async function searchExtensions(query) {
        try {
            extResultsContainer.innerHTML = '<div style="text-align:center; color:var(--text-muted); font-size:0.8rem; padding: 20px;">Searching Marketplace...</div>';
            
            const res = await fetch(`https://open-vsx.org/api/-/search?query=${encodeURIComponent(query)}&size=15`);
            if (!res.ok) throw new Error("Marketplace unavailable");
            
            const data = await res.json();
            
            if (data.extensions.length === 0) {
                extResultsContainer.innerHTML = '<div style="text-align:center; color:var(--text-muted); font-size:0.8rem; padding: 20px;">No extensions found.</div>';
                return;
            }

            extResultsContainer.innerHTML = '';
            
            data.extensions.forEach(ext => {
                extResultsContainer.appendChild(createExtensionCard(ext));
            });
            
        } catch (err) {
            console.error("Extension search failed:", err);
            extResultsContainer.innerHTML = `<div style="text-align:center; color:var(--danger); font-size:0.8rem; padding: 20px;">Marketplace Error: ${err.message}</div>`;
        }
    }

    // Initial load
    initFileTree();
    renderDefaultExtensionsView();
});
