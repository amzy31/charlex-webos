from flask import Blueprint, Response, request, render_template_string, jsonify, send_from_directory
import os
import uuid

window_manager_bp = Blueprint('window_manager', __name__)

# In-memory note storage
note_content = ""

js_code = """
let dragData = {
    dragging: false,
    offsetX: 0,
    offsetY: 0,
    targetId: null,
};

function startDrag(e, id) {
    dragData.dragging = true;
    dragData.targetId = id;
    const target = document.getElementById(id);
    dragData.offsetX = e.clientX - target.offsetLeft;
    dragData.offsetY = e.clientY - target.offsetTop;
    document.body.style.userSelect = 'none';
}

window.addEventListener('mousemove', (e) => {
    if (!dragData.dragging) return;
    const target = document.getElementById(dragData.targetId);
    let newX = e.clientX - dragData.offsetX;
    let newY = e.clientY - dragData.offsetY;
    // Keep window inside viewport
    newX = Math.max(0, Math.min(newX, window.innerWidth - target.offsetWidth));
    newY = Math.max(0, Math.min(newY, window.innerHeight - target.offsetHeight - 80)); // 80 for dock height + margin
    target.style.left = newX + 'px';
    target.style.top = newY + 'px';
});

window.addEventListener('mouseup', () => {
    dragData.dragging = false;
    document.body.style.userSelect = 'auto';
});

function closeWindow(id) {
    const win = document.getElementById(id);
    win.style.display = 'none';
}

function minimizeWindow(id) {
    const win = document.getElementById(id);
    win.style.display = 'none';
}

function maximizeWindow(id) {
    const win = document.getElementById(id);
    if (win.classList.contains('maximized')) {
        // Restore
        win.style.top = win.dataset.prevTop;
        win.style.left = win.dataset.prevLeft;
        win.style.width = '300px';
        win.style.height = 'auto';
        win.classList.remove('maximized');
    } else {
        // Maximize
        win.dataset.prevTop = win.style.top;
        win.dataset.prevLeft = win.style.left;
        win.style.top = '0px';
        win.style.left = '0px';
        win.style.width = '100vw';
        win.style.height = 'calc(100vh - 80px)';
        win.classList.add('maximized');
    }
}

function openWindow(id) {
    const win = document.getElementById(id);
    win.style.display = 'flex';
    win.style.zIndex = 1000;
}

// Save & Download button functionality
document.addEventListener('DOMContentLoaded', () => {
    const saveDownloadBtn = document.getElementById('saveDownloadBtn');
    if (saveDownloadBtn) {
        // Remove any existing click listeners to prevent multiple triggers
        saveDownloadBtn.replaceWith(saveDownloadBtn.cloneNode(true));
        const newSaveDownloadBtn = document.getElementById('saveDownloadBtn');
        newSaveDownloadBtn.addEventListener('click', async () => {
            const contentElem = document.getElementById('noteContent');
            if (!contentElem) {
                alert('Note content element not found');
                return;
            }
            const content = contentElem.value;
            try {
                const response = await fetch('/note/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ noteContent: content }),
                });
                if (!response.ok) {
                    throw new Error('Failed to save note');
                }
                const data = await response.json();
                const noteId = data.note_id;
                const downloadUrl = `/note/download/${noteId}`;
                // Trigger download
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = `${noteId}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } catch (error) {
                alert('Error saving and downloading note: ' + error.message);
            }
        });
    }
});
"""

@window_manager_bp.route('/window_manager.js')
def serve_js():
    return Response(js_code, mimetype='application/javascript')

@window_manager_bp.route('/note', methods=['GET', 'POST'])
def note():
    global note_content
    if request.method == 'POST':
        note_content = request.form.get('noteContent', '')
        return '', 204
    else:
        # Stream the note content as plain text
        return Response(note_content, mimetype='text/plain')

# Directory to save notes
SAVE_DIR = 'saved_notes'

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

@window_manager_bp.route('/note/save', methods=['POST'])
def save_note():
    data = request.get_json()
    content = data.get('noteContent', '')
    note_id = str(uuid.uuid4())
    filename = f"{note_id}.txt"
    filepath = os.path.join(SAVE_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'note_id': note_id})

@window_manager_bp.route('/note/download/<note_id>', methods=['GET'])
def download_note(note_id):
    filename = f"{note_id}.txt"
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)
