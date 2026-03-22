// Track staged photo filenames (newly uploaded, not yet saved to DB)
const stagedPhotos = [];

function updateStagedInput() {
    document.getElementById('staged-photos').value = stagedPhotos.join(',');
    const btn = document.getElementById('ai-analyse-btn');
    const hasAnyPhotos = document.querySelectorAll('#photo-preview .photo-thumb').length > 0;
    btn.style.display = hasAnyPhotos ? 'block' : 'none';
}

function addPhotoThumb(filename, url) {
    const grid = document.getElementById('photo-preview');
    const div = document.createElement('div');
    div.className = 'photo-thumb';
    div.dataset.filename = filename;
    div.innerHTML = `
        <img src="${url}" alt="">
        <button type="button" class="photo-remove" onclick="removePhoto(this)">&times;</button>
    `;
    grid.appendChild(div);
}

async function uploadFile(file) {
    const form = new FormData();
    form.append('photo', file);
    const res = await fetch('/api/photos/upload', { method: 'POST', body: form });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
}

async function handlePhotoCapture(input) {
    if (!input.files.length) return;
    const status = document.getElementById('ai-status');
    for (const file of input.files) {
        try {
            status.textContent = 'Uploading...';
            const data = await uploadFile(file);
            stagedPhotos.push(data.filename);
            addPhotoThumb(data.filename, data.url);
            status.textContent = '';
        } catch (e) {
            console.error(e);
            status.textContent = 'Upload failed: ' + e.message;
        }
    }
    updateStagedInput();
    input.value = '';
}

async function handlePhotoSelect(input) {
    await handlePhotoCapture(input);
}

function removePhoto(btn) {
    const thumb = btn.closest('.photo-thumb');
    const filename = thumb.dataset.filename;
    const photoId = thumb.dataset.photoId;

    // If this photo is already saved in DB, delete via API
    if (photoId) {
        fetch(`/api/photos/${photoId}/delete`, { method: 'POST' });
    }

    // Remove from staged list
    const idx = stagedPhotos.indexOf(filename);
    if (idx !== -1) stagedPhotos.splice(idx, 1);

    thumb.remove();
    updateStagedInput();
}

async function analyseWithAI() {
    const thumbs = document.querySelectorAll('#photo-preview .photo-thumb');
    const filenames = Array.from(thumbs).map(t => t.dataset.filename);
    if (!filenames.length) return;

    const btn = document.getElementById('ai-analyse-btn');
    const status = document.getElementById('ai-status');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Analysing...';
    status.textContent = '';

    try {
        const res = await fetch('/api/ai/analyse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filenames }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Analysis failed');
        }
        const data = await res.json();

        // Pre-fill form fields (only if currently empty)
        const fields = {
            name: 'f-name',
            description: 'f-description',
            category: 'f-category',
            brand: 'f-brand',
            serial_number: 'f-serial_number',
            purchase_price: 'f-purchase_price',
            condition: 'f-condition',
            notes: 'f-notes',
        };
        for (const [key, id] of Object.entries(fields)) {
            const el = document.getElementById(id);
            if (el && data[key] && !el.value) {
                el.value = data[key];
                el.dispatchEvent(new Event('change'));
            }
        }
        status.textContent = 'Fields pre-filled. Review and edit as needed.';
    } catch (e) {
        status.textContent = 'Error: ' + e.message;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyse with AI';
    }
}

function deleteItem(itemId) {
    if (confirm('Delete this item and all its photos?')) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/api/items/${itemId}/delete`;
        document.body.appendChild(form);
        form.submit();
    }
}

// Init
updateStagedInput();
