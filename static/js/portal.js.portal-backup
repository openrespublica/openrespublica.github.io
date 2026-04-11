// static/js/portal.js

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFileDrop();
    initUploadForm();
    initIngestForm();
    initLedgerPagination();
    loadDashboard();
});

// ── NAVIGATION ──
function initNavigation() {
    document.querySelectorAll('.nav-item[data-target]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const target = e.currentTarget.getAttribute('data-target');
            
            // Toggle active classes on buttons
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            // Toggle active classes on panels
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel-' + target).classList.add('active');
            
            if (target === 'ledger') loadLedger();
            if (target === 'dashboard') loadDashboard();
        });
    });
}

// ── FILE DROP UX ──
function initFileDrop() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('pdfFile');
    
    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', e => { 
        e.preventDefault(); 
        dropZone.classList.add('dragover'); 
    });
    
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    
    dropZone.addEventListener('drop', e => {
        e.preventDefault(); 
        dropZone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file?.name.endsWith('.pdf')) { 
            fileInput.files = e.dataTransfer.files; 
            updateFileDisplay(fileInput); 
        }
    });

    fileInput.addEventListener('change', () => updateFileDisplay(fileInput));
}

function updateFileDisplay(input) {
    const file = input.files[0]; 
    if (!file) return;
    const el = document.getElementById('selectedFileName');
    el.textContent = `✓ ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
    el.style.display = 'inline-block';
    el.style.marginTop = '0.6rem';
    el.style.padding = '3px 10px';
    el.style.background = '#F0FAF4';
    el.style.color = '#1E7A3E';
    el.style.borderRadius = '4px';
    el.style.fontFamily = 'monospace';
}

// ── UI HELPERS ──
function setProgress(prefix, step, total) {
    for (let i = 1; i <= total; i++) {
        const el = document.getElementById(prefix + i); 
        if (!el) continue;
        el.className = 'progress-step' + (i < step ? ' done' : i === step ? ' active' : '');
    }
    const barId = prefix === 'us' ? 'uploadBar' : 'ingestBar';
    const bar = document.getElementById(barId);
    if (bar) bar.style.width = `${Math.min(100, (step/total)*100)}%`;
}

function showResult(id, ok, title, details, blob, filename) {
    const el = document.getElementById(id);
    el.className = 'result-box ' + (ok ? 'result-success' : 'result-error');
    el.style.display = 'block';
    
    let dHtml = '';
    if (details && typeof details === 'object') {
        dHtml = '<div class="result-kv">' + Object.entries(details).map(([k,v]) =>
            `<span class="result-key">${k}</span><span class="result-val">${v}</span>`
        ).join('') + '</div>';
    } else if (details) {
        dHtml = `<p style="margin-top:0.5rem;">${details}</p>`;
    }
    
    let dlHtml = '';
    if (blob && filename) { 
        const url = URL.createObjectURL(blob); 
        dlHtml = `<a href="${url}" download="${filename}" class="download-btn">⬇ Download ${filename}</a>`; 
    }
    el.innerHTML = `<div class="result-header"><h4>${ok?'✅':'❌'} ${title}</h4></div><div class="result-body">${dHtml}${dlHtml}</div>`;
}

// ── UPLOAD FORM ──
function initUploadForm() {
    document.getElementById('uploadForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const file = document.getElementById('pdfFile').files[0];
        if (!file) { alert('Please select a PDF file.'); return; }
        
        const docType = document.getElementById('uploadDocType').value;
        const btn = document.getElementById('uploadBtn');
        
        btn.disabled = true;
        document.getElementById('uploadProgress').style.display = 'block';
        document.getElementById('uploadResult').style.display = 'none';
        
        // Simulating processing stages for UI feedback
        [1,2,3].forEach((s,i) => setTimeout(() => setProgress('us',s,4), i*700+100));
        
        const fd = new FormData();
        fd.append('document', file);
        fd.append('doc_type', docType);
        
        try {
            const res = await fetch('/upload', {method:'POST', body:fd});
            setProgress('us',4,4);
            
            if (res.ok) {
                const blob = await res.blob();
                const ctrl = res.headers.get('Content-Disposition')?.match(/filename="?([^"]+)"?/)?.[1] || `${docType}.pdf`;
                showResult('uploadResult', true, 'Document Anchored to TruthChain',
                    {'File': file.name, 'Type': docType, 'Status': 'Anchored · Publishing to ledger...'}, blob, ctrl);
            } else { 
                showResult('uploadResult', false, 'Upload Failed', await res.text()); 
            }
        } catch(err) { 
            showResult('uploadResult', false, 'Connection Error', err.message); 
        } finally { 
            btn.disabled = false; 
            setTimeout(() => { 
                document.getElementById('uploadProgress').style.display='none'; 
                setProgress('us',0,4); 
            }, 3500); 
        }
    });
}

// ── PHILID INGEST ──
function initIngestForm() {
    document.getElementById('loadSampleBtn')?.addEventListener('click', () => {
        document.getElementById('philidPayload').value = JSON.stringify({
            subject: { fName:"Juan", mName:"dela", lName:"Cruz", Suffix:"", sex:"Male", DOB:"1990-01-15", POB:"Dumaguete City, Negros Oriental", PCN:"1234-5678-9012-3456" },
            alg: "ES256", signature: "SAMPLE-PSA-SIG-ABCDEF123456"
        }, null, 2);
    });

    document.getElementById('ingestForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const raw = document.getElementById('philidPayload').value.trim();
        if (!raw) { alert('Please paste a PhilID JSON payload.'); return; }
        
        let parsed; 
        try { parsed = JSON.parse(raw); } catch { alert('Invalid JSON.'); return; }
        
        const btn = document.getElementById('ingestBtn'); 
        btn.disabled = true;
        document.getElementById('ingestProgress').style.display = 'block';
        document.getElementById('ingestResult').style.display = 'none';
        
        [1,2,3,4].forEach((s,i) => setTimeout(() => setProgress('is',s,5), [100,700,2200,4000][i]));
        
        try {
            const res = await fetch('/ingest', {
                method:'POST', 
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ payload: JSON.stringify(parsed), purok: document.getElementById('ingestPurok').value, purpose: document.getElementById('ingestPurpose').value })
            });
            
            setProgress('is',5,5);
            
            if (res.ok) {
                const blob = await res.blob();
                const ctrl = res.headers.get('Content-Disposition')?.match(/filename="?([^"]+)"?/)?.[1] || 'certificate.pdf';
                const s = parsed.subject || {};
                showResult('ingestResult', true, 'Certificate Generated & Anchored',
                    {'Name': `${s.fName||''} ${s.mName||''} ${s.lName||''}`.trim(), 'PCN': s.PCN||'—', 'Status':'Anchored · Publishing to ledger...'}, blob, ctrl);
            } else { 
                const d = await res.json().catch(()=>({message:'Unknown error'})); 
                showResult('ingestResult', false, 'Ingest Failed', d.message); 
            }
        } catch(err) { 
            showResult('ingestResult', false, 'Connection Error', err.message); 
        } finally { 
            btn.disabled = false; 
            setTimeout(() => { 
                document.getElementById('ingestProgress').style.display='none'; 
                setProgress('is',0,5); 
            }, 4000); 
        }
    });
}

// ── LEDGER & DASHBOARD LOGIC ──
let lData=[], lPage=1; const LP=15;

async function loadLedger() {
    document.getElementById('ledgerBody').innerHTML = '<tr><td colspan="6" style="text-align:center;padding:1.5rem;color:var(--muted);"><div class="spinner" style="margin:0 auto 0.5rem;"></div>Loading...</td></tr>';
    try {
        const res = await fetch('https://openrespublica.github.io/records/manifest.json?t='+Date.now());
        if (!res.ok) throw new Error();
        lData = (await res.json()).reverse();
        renderLedgerTable();
    } catch { 
        document.getElementById('ledgerBody').innerHTML = '<tr><td colspan="6" style="text-align:center;padding:1.5rem;color:var(--muted);">Could not load manifest.</td></tr>'; 
    }
}

function renderLedgerTable() {
    const total=lData.length, start=(lPage-1)*LP, end=Math.min(start+LP,total), slice=lData.slice(start,end);
    document.getElementById('ledgerBody').innerHTML = slice.map(r => `
        <tr>
            <td><strong style="font-size:0.78rem;color:var(--navy-mid);">${r.control_number||'—'}</strong></td>
            <td><span class="badge-type">${r.document_type||'GENERAL'}</span></td>
            <td style="font-size:0.75rem;color:var(--muted);">${r.timestamp||'—'}</td>
            <td><span class="mono">${(r.sha256_hash||'').substring(0,14)}...</span></td>
            <td><span class="mono">#${r.immudb_transaction_id||'—'}</span></td>
            <td style="text-align:center;"><a href="https://openrespublica.github.io/index.html?hash=${r.sha256_hash}" target="_blank" class="btn-outline">Verify</a></td>
        </tr>`).join('');
        
    document.getElementById('ledgerCount').textContent = `Showing ${start+1}–${end} of ${total} records`;
    document.getElementById('lPrev').disabled = lPage === 1;
    document.getElementById('lNext').disabled = end >= total;
}

function initLedgerPagination() {
    document.getElementById('lPrev')?.addEventListener('click', () => {
        lPage = Math.max(1, lPage - 1);
        renderLedgerTable();
    });
    document.getElementById('lNext')?.addEventListener('click', () => {
        lPage = Math.min(lPage + 1, Math.ceil(lData.length / LP));
        renderLedgerTable();
    });
}

async function loadDashboard() {
    try {
        const res = await fetch('https://openrespublica.github.io/records/manifest.json?t='+Date.now());
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('dTotal').textContent = data.length;
        if (data.length) {
            document.getElementById('dLatest').textContent = ([...data].reverse()[0].timestamp||'').split(' ')[0]||'—';
        }
    } catch {}
}

document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    document.querySelectorAll('.nav-item[data-target]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const target = e.currentTarget.getAttribute('data-target');
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            e.currentTarget.classList.add('active');
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById('panel-' + target).classList.add('active');
            if(target === 'ledger') loadLedger();
        });
    });

    // File Drop
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('pdfFile');
    dropZone.onclick = () => fileInput.click();
    fileInput.onchange = () => {
        const name = fileInput.files[0]?.name;
        const el = document.getElementById('selectedFileName');
        el.textContent = name; el.style.display = 'block';
    };

    // Form Submit
    document.getElementById('uploadForm').onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData();
        fd.append('document', fileInput.files[0]);
        fd.append('doc_type', document.getElementById('uploadDocType').value);
        
        const res = await fetch('/upload', {method:'POST', body:fd});
        if(res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = "stamped_document.pdf"; a.click();
            document.getElementById('uploadResult').innerHTML = "✅ Document Anchored and Downloaded.";
        }
    };

    // Lock Engine (Kill Switch)
    document.getElementById('lockBtn').onclick = async () => {
        if(confirm("Shut down engine and purge RAM disk?")) {
            await fetch('/lock_engine', {method:'POST'});
            document.body.innerHTML = "<div style='text-align:center;padding:5rem;'><h1>🏛️ Engine Locked</h1><p>RAM disk purged. Session closed.</p></div>";
        }
    };
});

async function loadLedger() {
    const res = await fetch('https://openrespublica.github.io/records/manifest.json');
    const data = await res.json();
    document.getElementById('ledgerBody').innerHTML = data.slice(-10).reverse().map(r => `
        <tr>
            <td><span class="mono">${r.control_number}</span></td>
            <td><span class="badge-type">${r.document_type}</span></td>
            <td>${r.timestamp}</td>
            <td><a href="https://openrespublica.github.io/index.html?hash=${r.sha256_hash}" target="_blank">Verify</a></td>
        </tr>
    `).join('');
}
