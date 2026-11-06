"""Bright, minimal, Apple-style Stitch UI template for the Forest Wheel Plate Removal System.

Implements the 4 Stitch MCP screens from Project 'ForestWheel Plate Removal System':
1. SCREEN 1 — UPLOAD ('Web Upload & Plate Detection' / 'Upload & Plate Detection'):
   - Large dashed drop zone with 'Upload photos' / 'Select Multiple Photos' button (bulk upload).
   - Thumbnail grid with animated radial SVG progress ring per photo
     (Detecting plate → Removing plate → Done).
   - Input field 'Plate number' per batch (auto-filled when files are selected/detected, editable),
     plus vehicle title/price metadata and masking style selector.
   - Primary button 'Process & Save'.
2. SCREEN 2 — GALLERY ('Web Vehicle Gallery' / 'Vehicle Gallery', grouped by plate number):
   - Top search bar (search by plate number or model) + status filter pills.
   - Top-right 'Select' button to enter selection mode.
   - Each car is a group card: plate number title badge (e.g. SXX 1234 A), editable vehicle title,
     photo count, Before/After toggle (Original vs Plate Removed), and 3-4 preview thumbnails.
   - Tap a group to open a full grid view of all photos for that car with Before/After toggle,
     single-photo delete, edit group details, or open in Frame Studio.
3. SCREEN 3 — FRAME TEMPLATE EDITOR ('Web Frame Studio' / 'Frame Template Editor'):
   - Pick any photo from any car group, then choose frame ratio with a segmented control: 1:1, 16:9, 9:16.
   - Canvas preview shows the photo inside the chosen frame.
   - Fit mode toggle:
     • 'Fit to frame': whole photo is visible, empty space filled with a blurred, enlarged copy of the same photo.
     • 'Fill frame': photo is cropped to cover the whole frame, with drag/pinch to reposition.
   - Apple-style template row below the canvas: Clean White, Soft Grey, Minimal Border, Rounded Card, Glass Overlay.
     Each has an optional toggleable small caption area (car model, price).
   - Buttons: 'Save to Gallery' and 'Export'.
4. SCREEN 4 — DELETE / SELECTION MODE ('Web Selection & Delete Modal' / 'Gallery Selection & Delete Modal'):
   - In Gallery, tapping 'Select' shows checkmarks on photos and on car groups.
   - Floating bottom action bar: 'Select All', 'Delete Selected (n)', plus scope options:
     'Delete selected photos only', 'Delete entire car group', and 'Delete all photos'.
   - Confirmation bottom sheet / modal with red destructive button and Cancel, showing exact item count.
"""

STITCH_UI_HTML = r"""<!DOCTYPE html>
<html class="light" lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0, viewport-fit=cover" name="viewport"/>
<title>ForestWheel — Apple-Style Plate Removal &amp; Studio</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface": "#fcf8fb",
        "surface-bright": "#fcf8fb",
        "surface-dim": "#dcd9dc",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f6f3f5",
        "surface-container": "#f0edef",
        "surface-container-high": "#eae7ea",
        "surface-container-highest": "#e4e2e4",
        "on-surface": "#1b1b1d",
        "on-surface-variant": "#414755",
        "primary": "#0058bc",
        "primary-container": "#0070eb",
        "primary-fixed": "#d8e2ff",
        "on-primary": "#ffffff",
        "secondary": "#505f76",
        "secondary-container": "#d0e1fb",
        "tertiary": "#bc000a",
        "error": "#ba1a1a",
        "error-container": "#ffdad6",
        "on-error": "#ffffff",
        "outline": "#717786",
        "outline-variant": "#c1c6d7"
      },
      fontFamily: {
        "sans": ["-apple-system", "BlinkMacSystemFont", "SF Pro Display", "SF Pro Text", "Inter", "sans-serif"]
      },
      boxShadow: {
        "apple-card": "0 8px 30px rgba(27, 27, 29, 0.04), 0 2px 6px rgba(27, 27, 29, 0.02)",
        "apple-float": "0 20px 50px rgba(27, 27, 29, 0.12), 0 4px 12px rgba(27, 27, 29, 0.05)",
        "apple-sheet": "0 -12px 48px rgba(27, 27, 29, 0.16)"
      }
    }
  }
}
</script>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
    background-color: #fcf8fb;
    color: #1b1b1d;
    -webkit-font-smoothing: antialiased;
  }
  .material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 450, 'GRAD' 0, 'opsz' 24;
    vertical-align: middle;
  }
  .material-fill {
    font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;
  }
  .apple-glass {
    background: rgba(252, 248, 251, 0.82);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
  }
  .apple-card-white {
    background: #ffffff;
    border: 1px solid rgba(193, 198, 215, 0.28);
    box-shadow: 0 8px 30px rgba(27, 27, 29, 0.04), 0 2px 6px rgba(27, 27, 29, 0.02);
  }
  .no-scrollbar::-webkit-scrollbar { display: none; }
  .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
  @keyframes spinSlow { to { transform: rotate(360deg); } }
  .spin-ring { animation: spinSlow 1.3s linear infinite; transform-origin: center; }
</style>
</head>
<body class="bg-surface text-on-surface min-h-screen pb-28 md:pb-16 selection:bg-primary-fixed selection:text-primary">

<!-- Top Translucent Apple Navigation Bar -->
<header class="sticky top-0 z-40 apple-glass border-b border-outline-variant/25">
  <div class="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center text-white shadow-sm">
        <span class="material-symbols-outlined text-[20px] material-fill">directions_car</span>
      </div>
      <div>
        <span class="text-lg font-bold tracking-tight text-on-surface">ForestWheel</span>
        <span class="hidden sm:inline-block ml-2 text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant">Plate Studio</span>
      </div>
    </div>

    <!-- Desktop Segmented 3-Tab Switcher (Upload, Gallery, Frames) -->
    <nav class="hidden md:flex items-center bg-surface-container p-1 rounded-full border border-outline-variant/20">
      <button id="nav-desk-upload" onclick="switchTab('upload')" class="px-5 py-1.5 rounded-full text-sm font-semibold transition-all flex items-center gap-1.5 bg-white text-primary shadow-sm">
        <span class="material-symbols-outlined text-[18px]">cloud_upload</span>
        <span>Upload</span>
      </button>
      <button id="nav-desk-gallery" onclick="switchTab('gallery')" class="px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">photo_library</span>
        <span>Gallery</span>
        <span id="badge-desk-gallery" class="ml-1 px-1.5 py-0.2 text-[11px] rounded-full bg-surface-container-highest text-on-surface font-bold">0</span>
      </button>
      <button id="nav-desk-frames" onclick="switchTab('frames')" class="px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">crop_free</span>
        <span>Frames</span>
      </button>
    </nav>

    <!-- Right Quick Actions -->
    <div class="flex items-center gap-2.5">
      <button onclick="runDemoBatch()" id="btn-demo-load" class="px-3.5 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-xs font-semibold text-on-surface-variant transition-all flex items-center gap-1.5" title="Load sample vehicles from test_photos">
        <span class="material-symbols-outlined text-[16px] text-primary">auto_awesome</span>
        <span class="hidden sm:inline">Load Sample Cars</span>
      </button>
    </div>
  </div>
</header>

<!-- ========================================================================= -->
<!-- SCREEN 1: UPLOAD & PLATE DETECTION                                        -->
<!-- ========================================================================= -->
<main id="screen-upload" class="max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">
  <div class="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
    <div>
      <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface">Upload &amp; Plate Removal</h1>
      <p class="text-sm sm:text-base text-on-surface-variant mt-1">Select multiple car photos to automatically detect and mask license plates.</p>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
    <!-- Left Column: Dashed Drop Zone + Photo Progress Grid -->
    <div class="lg:col-span-8 space-y-6">
      <!-- Hidden file input -->
      <input id="upload-file-input" type="file" multiple accept=".jpg,.jpeg,.png,.heic,image/*" class="hidden" onchange="handleFilesSelected(this.files)"/>

      <!-- Large Dashed Drop Zone -->
      <div id="upload-dropzone"
           onclick="document.getElementById('upload-file-input').click()"
           ondragover="event.preventDefault(); this.classList.add('border-primary', 'bg-primary-fixed/20');"
           ondragleave="this.classList.remove('border-primary', 'bg-primary-fixed/20');"
           ondrop="event.preventDefault(); this.classList.remove('border-primary', 'bg-primary-fixed/20'); handleFilesSelected(event.dataTransfer.files);"
           class="apple-card-white rounded-[24px] p-8 sm:p-12 border-2 border-dashed border-primary/35 hover:border-primary transition-all cursor-pointer flex flex-col items-center justify-center text-center group">
        <div class="w-16 h-16 rounded-2xl bg-primary-fixed/60 text-primary flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
          <span class="material-symbols-outlined text-4xl">add_photo_alternate</span>
        </div>
        <h2 class="text-lg sm:text-xl font-semibold text-on-surface mb-1">Drop car photos here</h2>
        <p class="text-xs sm:text-sm text-on-surface-variant max-w-md mb-6">
          Bulk upload raw showroom photos (JPEG, PNG, HEIC). Plates are automatically detected and covered.
        </p>
        <button type="button" onclick="event.stopPropagation(); document.getElementById('upload-file-input').click();"
                class="bg-gradient-to-b from-primary-container to-primary text-white font-semibold px-7 py-3 rounded-full shadow-md hover:opacity-95 active:scale-[0.98] transition-all flex items-center gap-2 text-sm">
          <span class="material-symbols-outlined text-[20px]">upload_file</span>
          <span>Upload photos</span>
        </button>
      </div>

      <!-- Selected Photos Grid with Progress Rings (Detecting plate -> Removing plate -> Done) -->
      <div id="upload-queue-section" class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <h3 class="text-base sm:text-lg font-bold text-on-surface">Batch Queue</h3>
            <span id="upload-queue-badge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary-fixed text-primary">0 Photos</span>
          </div>
          <button type="button" onclick="clearUploadQueue()" class="text-xs font-semibold text-on-surface-variant hover:text-error transition-colors">
            Clear queue
          </button>
        </div>

        <div id="upload-thumbnails-grid" class="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <!-- Populated dynamically by JS -->
        </div>
      </div>
    </div>

    <!-- Right Column: Batch Plate Number & Process Inspector -->
    <div class="lg:col-span-4 lg:sticky lg:top-24">
      <div class="apple-card-white rounded-[24px] p-6 sm:p-7 space-y-6">
        <div class="flex items-center justify-between border-b border-surface-container pb-4">
          <div>
            <span class="text-[11px] font-bold uppercase tracking-widest text-primary block">Batch Settings</span>
            <h3 class="text-lg font-bold text-on-surface mt-0.5">Vehicle Group</h3>
          </div>
          <span id="upload-detection-pill" class="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 flex items-center gap-1">
            <span class="material-symbols-outlined text-[14px] material-fill">verified</span>
            <span>Auto-Grouping</span>
          </span>
        </div>

        <!-- Input Field: Plate Number per batch (auto-filled when detected/selected, editable) -->
        <div class="space-y-3">
          <div>
            <label for="input-plate-number" class="block text-xs font-semibold text-on-surface-variant mb-1.5">
              Plate number <span class="text-outline font-normal">(Car group ID, editable)</span>
            </label>
            <div class="relative">
              <input id="input-plate-number" type="text" value="SXX 1234 A" placeholder="e.g. SXX 1234 A"
                     class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-2xl px-4 py-3 text-base font-bold tracking-wider uppercase text-on-surface focus:ring-2 focus:ring-primary/15 transition-all"/>
              <span class="material-symbols-outlined text-primary text-lg absolute right-3.5 top-3.5" title="Auto-filled on batch selection">pin</span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="input-car-model" class="block text-xs font-semibold text-on-surface-variant mb-1">Car Model</label>
              <input id="input-car-model" type="text" value="2023 Porsche 911 GT3" placeholder="e.g. Porsche 911"
                     class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-xl px-3 py-2 text-xs font-semibold text-on-surface"/>
            </div>
            <div>
              <label for="input-car-price" class="block text-xs font-semibold text-on-surface-variant mb-1">Listing Price</label>
              <input id="input-car-price" type="text" value="$248,900" placeholder="e.g. $248,900"
                     class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-xl px-3 py-2 text-xs font-semibold text-primary"/>
            </div>
          </div>
        </div>

        <!-- Default Frame Ratio for Batch -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="block text-xs font-semibold text-on-surface-variant">Output Aspect Ratio</label>
            <button type="button" onclick="switchTab('frames')" class="text-[11px] font-semibold text-primary hover:underline flex items-center gap-0.5">
              <span>Preset: <strong id="upload-active-preset-pill">Clean White • Fit</strong></span>
              <span class="material-symbols-outlined text-[13px]">tune</span>
            </button>
          </div>
          <div class="grid grid-cols-3 gap-1.5 bg-surface-container p-1 rounded-2xl">
            <button type="button" onclick="setUploadRatio('1:1')" id="up-ratio-1:1" class="py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">1:1</button>
            <button type="button" onclick="setUploadRatio('16:9')" id="up-ratio-16:9" class="py-2 rounded-xl text-xs font-bold bg-white text-primary shadow-sm transition-all">16:9</button>
            <button type="button" onclick="setUploadRatio('9:16')" id="up-ratio-9:16" class="py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">9:16</button>
          </div>
        </div>

        <!-- Primary Button: Process & Save -->
        <div class="pt-2 space-y-2.5">
          <button id="btn-process-save" type="button" onclick="submitUploadBatch()"
                  class="w-full py-4 rounded-2xl bg-gradient-to-b from-primary-container to-primary text-white font-semibold text-base shadow-lg shadow-primary/20 hover:opacity-95 active:scale-[0.98] transition-all flex items-center justify-center gap-2">
            <span class="material-symbols-outlined text-[20px]">bolt</span>
            <span id="btn-process-save-label">Process &amp; Save</span>
          </button>
          <p id="upload-status-msg" class="text-[11px] text-center text-on-surface-variant">
            Original photos are never modified. Uncertain plates route to Review.
          </p>
        </div>
      </div>
    </div>
  </div>
</main>

<!-- ========================================================================= -->
<!-- SCREEN 2: VEHICLE GALLERY (GROUPED BY PLATE NUMBER) + SELECTION MODE      -->
<!-- ========================================================================= -->
<main id="screen-gallery" class="hidden max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">
  <!-- Header Row + Search Bar + Top-Right "Select" Button -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
    <div>
      <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface">Vehicle Gallery</h1>
      <p id="gallery-subtitle" class="text-sm text-on-surface-variant mt-0.5">Grouped by plate number • Toggle Original vs Plate Removed</p>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <!-- Search Bar at Top (search by plate number) -->
      <div class="relative flex-1 sm:w-72">
        <span class="material-symbols-outlined text-outline text-[20px] absolute left-3.5 top-2.5">search</span>
        <input id="gallery-search-input" type="text" oninput="renderGallery()" placeholder="Search by plate number (e.g. SXX1234A)..."
               class="w-full pl-10 pr-4 py-2.5 bg-white border border-outline-variant/40 rounded-full text-sm text-on-surface placeholder:text-outline focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all shadow-sm"/>
      </div>

      <!-- Top-Right "Select" Button to enter Selection Mode -->
      <button id="btn-toggle-select-mode" type="button" onclick="toggleSelectionMode()"
              class="px-5 py-2.5 rounded-full font-semibold text-sm border border-outline-variant/50 bg-white hover:bg-surface-container-low text-on-surface transition-all flex items-center gap-1.5 shadow-sm">
        <span class="material-symbols-outlined text-[18px] text-primary" id="icon-select-mode">check_circle</span>
        <span id="label-select-mode">Select</span>
      </button>
    </div>
  </div>

  <!-- Filter Pills & Global Before/After Toggle -->
  <div class="flex flex-wrap items-center justify-between gap-3 mb-7 pb-3 border-b border-outline-variant/25">
    <div class="flex items-center gap-2 overflow-x-auto no-scrollbar">
      <button type="button" onclick="setGalleryFilter('all')" id="flt-all" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-on-surface text-white transition-all">All Cars</button>
      <button type="button" onclick="setGalleryFilter('ready')" id="flt-ready" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant hover:text-on-surface transition-all">Plate Removed</button>
      <button type="button" onclick="setGalleryFilter('review')" id="flt-review" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant hover:text-on-surface transition-all">Needs Review</button>
    </div>

    <div class="flex items-center gap-2">
      <!-- Global Before / After Default Toggle -->
      <div class="inline-flex items-center bg-surface-container p-1 rounded-full border border-outline-variant/25">
        <button type="button" onclick="setGlobalCompareMode('after')" id="btn-global-after" class="px-3.5 py-1 rounded-full text-xs font-semibold bg-white text-primary shadow-sm transition-all">Plate Removed</button>
        <button type="button" onclick="setGlobalCompareMode('before')" id="btn-global-before" class="px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">Original (Before)</button>
      </div>

      <!-- More Menu for "Delete all photos" -->
      <button type="button" onclick="openDeleteModal('all')" class="px-3.5 py-1.5 rounded-full text-xs font-semibold text-error hover:bg-error-container/40 transition-colors flex items-center gap-1" title="Delete all photos in inventory">
        <span class="material-symbols-outlined text-[16px]">delete_sweep</span>
        <span class="hidden sm:inline">Delete All</span>
      </button>
    </div>
  </div>

  <!-- Gallery Group Cards Grid (2 columns on desktop, 1 on mobile) -->
  <div id="gallery-cards-container" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Populated dynamically by renderGallery() -->
  </div>
</main>

<!-- ========================================================================= -->
<!-- SCREEN 3: FRAME TEMPLATE EDITOR (FRAMES)                                  -->
<!-- ========================================================================= -->
<main id="screen-frames" class="hidden max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
    <div>
      <span class="text-xs font-bold uppercase tracking-widest text-primary">Showroom Studio</span>
      <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface mt-0.5">Frame Template Editor</h1>
    </div>
    <!-- Vehicle & Photo Picker -->
    <div class="flex flex-wrap items-center gap-2.5">
      <select id="frame-car-select" onchange="onFrameCarChange()" class="bg-white border border-outline-variant/40 rounded-full px-4 py-2 text-xs font-semibold text-on-surface shadow-sm focus:border-primary focus:ring-primary">
      </select>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
    <!-- Left / Center: Interactive Frame Canvas + Apple Template Row -->
    <div class="lg:col-span-8 space-y-5">
      <!-- Top Controls Bar: Segmented Ratio (1:1, 16:9, 9:16) + Fit Mode Toggle (Fit to Frame vs Fill Frame) -->
      <div class="apple-card-white rounded-2xl p-3 flex flex-wrap items-center justify-between gap-3">
        <!-- Segmented Control: 1:1, 16:9, 9:16 -->
        <div class="flex items-center bg-surface-container p-1 rounded-xl">
          <button type="button" onclick="setStudioRatio('1:1')" id="st-ratio-1:1" class="px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all">1:1 Square</button>
          <button type="button" onclick="setStudioRatio('16:9')" id="st-ratio-16:9" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">16:9 Wide</button>
          <button type="button" onclick="setStudioRatio('9:16')" id="st-ratio-9:16" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">9:16 Story</button>
        </div>

        <!-- Fit Mode Toggle: "Fit to frame" (blurred background) vs "Fill frame" (crop + drag to reposition) -->
        <div class="flex items-center bg-surface-container p-1 rounded-xl">
          <button type="button" onclick="setStudioFitMode('fit')" id="st-fit-fit" class="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[16px]">fit_screen</span>
            <span>Fit to frame (Blur BG)</span>
          </button>
          <button type="button" onclick="setStudioFitMode('fill')" id="st-fit-fill" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[16px]">aspect_ratio</span>
            <span>Fill frame (Crop &amp; Drag)</span>
          </button>
        </div>
      </div>

      <!-- Canvas Preview Stage -->
      <div class="apple-card-white rounded-[28px] p-4 sm:p-8 flex flex-col items-center justify-center min-h-[380px] sm:min-h-[480px] relative overflow-hidden bg-surface-container-low">
        <div id="studio-canvas-wrapper"
             onmousedown="startCanvasPan(event)"
             onmousemove="moveCanvasPan(event)"
             onmouseup="endCanvasPan()"
             onmouseleave="endCanvasPan()"
             ontouchstart="startCanvasPan(event)"
             ontouchmove="moveCanvasPan(event)"
             ontouchend="endCanvasPan()"
             class="relative rounded-2xl overflow-hidden shadow-apple-float transition-all select-none cursor-grab active:cursor-grabbing bg-white flex items-center justify-center max-h-[440px]">
          <img id="studio-preview-img" src="/api/frame-render?ratio=1:1&fit_mode=fit&template_style=clean_white" alt="Frame Studio Preview" class="max-h-[420px] w-auto object-contain pointer-events-none"/>
          <div id="studio-pan-hint" class="hidden absolute top-3 left-1/2 -translate-x-1/2 apple-glass px-3.5 py-1 rounded-full text-[11px] font-semibold text-on-surface shadow-sm border border-white/50 flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[14px] text-primary">open_with</span>
            <span>Drag photo to reposition crop</span>
          </div>
        </div>
      </div>

      <!-- Apple-style Template Row below Canvas: Clean White, Soft Grey, Minimal Border, Rounded Card, Glass Overlay -->
      <div class="apple-card-white rounded-[24px] p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Apple Studio Templates</span>
          <span id="studio-active-template-label" class="text-xs font-semibold text-primary">Clean White</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <button type="button" onclick="setStudioTemplate('clean_white')" id="tpl-clean_white" class="p-3 rounded-2xl border-2 border-primary bg-primary-fixed/15 text-left transition-all">
            <div class="h-12 rounded-xl bg-white border border-outline-variant/40 mb-2 flex items-end p-1.5 shadow-sm">
              <div class="w-full h-2 rounded bg-surface-container-high"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Clean White</p>
            <p class="text-[10px] text-on-surface-variant">Pure gallery card</p>
          </button>

          <button type="button" onclick="setStudioTemplate('soft_grey')" id="tpl-soft_grey" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-[#e4e2e4] border border-outline-variant/40 mb-2 flex items-end p-1.5">
              <div class="w-full h-2 rounded bg-white"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Soft Grey</p>
            <p class="text-[10px] text-on-surface-variant">Warm ambient matte</p>
          </button>

          <button type="button" onclick="setStudioTemplate('minimal_border')" id="tpl-minimal_border" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-white border-2 border-on-surface mb-2 flex items-center justify-center p-1.5">
              <div class="w-full h-full border border-outline-variant/60 rounded-sm"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Minimal Border</p>
            <p class="text-[10px] text-on-surface-variant">Crisp keyline inset</p>
          </button>

          <button type="button" onclick="setStudioTemplate('rounded_card')" id="tpl-rounded_card" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-surface-container-high p-2 mb-2 flex items-center justify-center">
              <div class="w-full h-full rounded-xl bg-white shadow-sm"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Rounded Card</p>
            <p class="text-[10px] text-on-surface-variant">iOS floating radius</p>
          </button>

          <button type="button" onclick="setStudioTemplate('glass_overlay')" id="tpl-glass_overlay" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 mb-2 flex items-end p-1.5">
              <div class="w-full h-3 rounded-lg bg-white/80 backdrop-blur-sm border border-white"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Glass Overlay</p>
            <p class="text-[10px] text-on-surface-variant">Frosted caption bar</p>
          </button>
        </div>
      </div>
    </div>

    <!-- Right Column: Plate Cover Upload + Photo Angle Selector + Optional Caption + Save Preset -->
    <div class="lg:col-span-4 space-y-6">
      <div class="apple-card-white rounded-[24px] p-6 space-y-5">
        <!-- Custom Plate Cover Image Upload -->
        <div class="space-y-3 pb-4 border-b border-surface-container">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-bold text-on-surface">Plate Cover Template</h4>
              <p class="text-[11px] text-on-surface-variant">Upload the graphic/logo used to cover license plates</p>
            </div>
            <span id="overlay-status-badge" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-primary-fixed text-primary">Active</span>
          </div>

          <input id="plate-overlay-file-input" type="file" accept=".png,.jpg,.jpeg,.webp,image/*" class="hidden" onchange="uploadCustomPlateOverlay(this.files)"/>

          <div class="flex items-center gap-3 bg-surface-container-low p-3 rounded-2xl border border-outline-variant/30">
            <div class="w-24 h-12 rounded-xl bg-white border border-outline-variant/40 flex items-center justify-center overflow-hidden shrink-0 p-1 shadow-xs">
              <img id="plate-overlay-preview-img" src="/media/plate-overlay" alt="Plate Cover" class="max-h-full max-w-full object-contain"/>
            </div>
            <div class="flex-1 flex flex-col gap-1.5">
              <button type="button" onclick="document.getElementById('plate-overlay-file-input').click()"
                      class="w-full py-1.5 px-3 rounded-xl bg-primary text-white text-xs font-semibold hover:opacity-95 transition-all flex items-center justify-center gap-1">
                <span class="material-symbols-outlined text-[15px]">upload</span>
                <span>Upload Plate Cover</span>
              </button>
              <button type="button" onclick="resetCustomPlateOverlay()"
                      class="w-full py-1 px-3 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-[11px] font-semibold transition-all">
                Reset to Default
              </button>
            </div>
          </div>
          <p id="overlay-upload-feedback" class="text-[11px] text-emerald-700 font-medium hidden"></p>
        </div>

        <!-- Angle / Photo Queue for Selected Car -->
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2.5">Preview Photo</label>
          <div id="frame-photo-strip" class="grid grid-cols-4 gap-2 max-h-44 overflow-y-auto p-1">
            <!-- Populated by JS -->
          </div>
        </div>

        <!-- Optional Small Caption Area (Car Model, Price) -->
        <div class="pt-4 border-t border-surface-container space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-bold text-on-surface">Showroom Caption</h4>
              <p class="text-[11px] text-on-surface-variant">Optional car model &amp; price badge</p>
            </div>
            <input id="studio-caption-toggle" type="checkbox" checked onchange="saveGlobalFramePreset(true)"
                   class="w-5 h-5 rounded-md text-primary focus:ring-primary border-outline-variant"/>
          </div>

          <div id="studio-caption-inputs" class="space-y-2.5">
            <div>
              <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Car Model</label>
              <input id="studio-model-input" type="text" value="2023 Porsche 911 GT3" oninput="debouncedRefreshStudio()"
                     class="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-3.5 py-2 text-xs font-semibold text-on-surface"/>
            </div>
            <div class="grid grid-cols-2 gap-2.5">
              <div>
                <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Price</label>
                <input id="studio-price-input" type="text" value="$248,900" oninput="debouncedRefreshStudio()"
                       class="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-3.5 py-2 text-xs font-bold text-primary"/>
              </div>
              <div>
                <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Subtitle / Specs</label>
                <input id="studio-specs-input" type="text" value="4,200 mi • PDK" oninput="debouncedRefreshStudio()"
                       class="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-3.5 py-2 text-xs text-on-surface"/>
              </div>
            </div>
          </div>
        </div>

        <!-- Primary Action Buttons: Apply Frame Config to All Uploads & Export -->
        <div class="pt-3 space-y-2.5">
          <button type="button" onclick="saveGlobalFramePreset(false)" id="btn-save-frame-preset"
                  class="w-full py-3.5 rounded-2xl bg-gradient-to-b from-primary-container to-primary text-white font-semibold text-sm shadow-lg shadow-primary/20 hover:opacity-95 active:scale-[0.98] transition-all flex items-center justify-center gap-2">
            <span class="material-symbols-outlined text-[19px]">check_circle</span>
            <span>Save as Default Upload Frame</span>
          </button>
          <div class="grid grid-cols-2 gap-2.5">
            <button type="button" onclick="saveStudioFrameToGallery()" id="btn-save-frame-gallery"
                    class="py-3 rounded-2xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
              <span class="material-symbols-outlined text-[17px] text-primary">bookmark_add</span>
              <span>Save Copy</span>
            </button>
            <button type="button" onclick="exportStudioFrame()"
                    class="py-3 rounded-2xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
              <span class="material-symbols-outlined text-[17px] text-primary">ios_share</span>
              <span>Export JPG</span>
            </button>
          </div>
          <p id="studio-save-feedback" class="text-[11px] text-center text-emerald-700 font-medium hidden"></p>
        </div>
      </div>
    </div>
  </div>
</main>

<!-- ========================================================================= -->
<!-- CAR GROUP EXPANDED MODAL (ALL PHOTOS + BEFORE/AFTER TOGGLE + EDIT/DELETE) -->
<!-- ========================================================================= -->
<div id="car-detail-modal" class="fixed inset-0 z-50 hidden bg-black/35 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6">
  <div class="bg-white rounded-[28px] max-w-5xl w-full max-h-[90vh] flex flex-col shadow-apple-float overflow-hidden border border-outline-variant/30">
    <!-- Modal Header -->
    <div class="px-6 py-4 border-b border-surface-container flex flex-wrap items-center justify-between gap-3 bg-surface">
      <div class="flex items-center gap-3">
        <span id="modal-car-plate-badge" class="px-3.5 py-1.5 rounded-xl bg-primary-fixed text-primary font-extrabold text-sm tracking-wider uppercase">SXX 1234 A</span>
        <div>
          <h3 id="modal-car-title" class="text-lg font-bold text-on-surface">2023 Porsche 911 GT3</h3>
          <p id="modal-car-count" class="text-xs text-on-surface-variant">0 photos</p>
        </div>
        <button type="button" onclick="toggleEditCarGroupForm()" class="p-1.5 rounded-full hover:bg-surface-container text-on-surface-variant" title="Edit plate number or car model">
          <span class="material-symbols-outlined text-[18px]">edit</span>
        </button>
      </div>

      <div class="flex items-center gap-2.5">
        <!-- Before / After Toggle inside Car Modal -->
        <div class="inline-flex items-center bg-surface-container p-1 rounded-full">
          <button type="button" onclick="setModalCompareMode('after')" id="modal-btn-after" class="px-3.5 py-1 rounded-full text-xs font-bold bg-white text-primary shadow-sm">Plate Removed</button>
          <button type="button" onclick="setModalCompareMode('before')" id="modal-btn-before" class="px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant">Original (Before)</button>
        </div>

        <button type="button" onclick="openDeleteModal('car', activeModalCarId)" class="px-3 py-1.5 rounded-full bg-error-container/50 hover:bg-error-container text-error text-xs font-semibold flex items-center gap-1">
          <span class="material-symbols-outlined text-[16px]">delete</span>
          <span>Delete Group</span>
        </button>

        <button type="button" onclick="closeCarDetailModal()" class="w-9 h-9 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center text-on-surface">
          <span class="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>
    </div>

    <!-- Inline Edit Car Group Drawer (Hidden by default) -->
    <div id="modal-edit-car-drawer" class="hidden px-6 py-4 bg-surface-container-low border-b border-outline-variant/30">
      <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Plate Number (Group ID)</label>
          <input id="edit-car-plate" type="text" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs font-bold uppercase text-on-surface"/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Car Model</label>
          <input id="edit-car-model" type="text" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs font-semibold text-on-surface"/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Price</label>
          <input id="edit-car-price" type="text" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs font-semibold text-primary"/>
        </div>
        <div class="flex gap-2">
          <button type="button" onclick="saveCarGroupMetadata()" class="flex-1 py-2 rounded-xl bg-primary text-white text-xs font-semibold">Save Changes</button>
          <button type="button" onclick="toggleEditCarGroupForm()" class="px-3 py-2 rounded-xl bg-surface-container text-xs font-semibold">Cancel</button>
        </div>
      </div>
    </div>

    <!-- All Photos Grid inside Modal -->
    <div id="modal-photos-grid" class="p-6 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 flex-1">
      <!-- Populated by JS -->
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- SCREEN 4: FLOATING SELECTION ACTION BAR & DELETE CONFIRMATION SHEET/MODAL -->
<!-- ========================================================================= -->
<div id="selection-floating-bar" class="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-40 hidden w-[94%] max-w-2xl">
  <div class="apple-glass bg-white/90 border border-outline-variant/40 rounded-full px-5 py-3 shadow-apple-float flex flex-wrap items-center justify-between gap-3">
    <div class="flex items-center gap-3">
      <button type="button" onclick="selectAllGalleryItems()" class="text-xs sm:text-sm font-semibold text-primary hover:underline">
        Select All
      </button>
      <span class="text-outline-variant">•</span>
      <button type="button" onclick="clearAllSelections()" class="text-xs sm:text-sm font-medium text-on-surface-variant hover:text-on-surface">
        Deselect
      </button>
      <span id="selection-counter-pill" class="px-2.5 py-0.5 rounded-full bg-primary-fixed text-primary text-xs font-bold">0 selected</span>
    </div>

    <div class="flex items-center gap-2">
      <button type="button" onclick="openDeleteModal('selected')" id="btn-floating-delete"
              class="px-5 py-2 rounded-full bg-error text-white text-xs sm:text-sm font-semibold shadow-sm hover:opacity-95 active:scale-95 transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">delete</span>
        <span id="btn-floating-delete-label">Delete Selected (0)</span>
      </button>
    </div>
  </div>
</div>

<!-- Apple-Style Confirmation Bottom Sheet / Modal for Delete -->
<div id="delete-confirm-modal" class="fixed inset-0 z-50 hidden bg-black/35 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
  <div class="bg-white w-full sm:max-w-md rounded-t-[28px] sm:rounded-[28px] p-6 sm:p-7 shadow-apple-sheet border border-outline-variant/30 space-y-5">
    <div class="w-10 h-1.5 bg-surface-container-highest rounded-full mx-auto sm:hidden"></div>

    <div class="flex items-start gap-4">
      <div class="w-12 h-12 rounded-2xl bg-error-container text-error flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-2xl">delete_forever</span>
      </div>
      <div>
        <h3 id="delete-modal-title" class="text-lg font-bold text-on-surface">Confirm Deletion</h3>
        <p id="delete-modal-desc" class="text-xs sm:text-sm text-on-surface-variant mt-1">
          Choose what you want to remove from the showroom gallery.
        </p>
      </div>
    </div>

    <!-- Deletion Scope Options: Selected photos, Entire car group, or All photos -->
    <div class="space-y-2 bg-surface-container-low p-3 rounded-2xl border border-outline-variant/30">
      <label class="flex items-center justify-between p-2.5 rounded-xl hover:bg-white cursor-pointer transition-colors">
        <div class="flex items-center gap-2.5">
          <input type="radio" name="delete-scope-radio" value="selected" checked onchange="updateDeleteModalSummary()" class="text-error focus:ring-error"/>
          <span class="text-xs sm:text-sm font-semibold text-on-surface">Delete selected photos only</span>
        </div>
        <span id="del-count-selected" class="text-xs font-bold text-on-surface-variant">0 photos</span>
      </label>

      <label class="flex items-center justify-between p-2.5 rounded-xl hover:bg-white cursor-pointer transition-colors">
        <div class="flex items-center gap-2.5">
          <input type="radio" name="delete-scope-radio" value="car" onchange="updateDeleteModalSummary()" class="text-error focus:ring-error"/>
          <span class="text-xs sm:text-sm font-semibold text-on-surface">Delete entire car group</span>
        </div>
        <span id="del-count-car" class="text-xs font-bold text-on-surface-variant">1 group</span>
      </label>

      <label class="flex items-center justify-between p-2.5 rounded-xl hover:bg-white cursor-pointer transition-colors">
        <div class="flex items-center gap-2.5">
          <input type="radio" name="delete-scope-radio" value="all" onchange="updateDeleteModalSummary()" class="text-error focus:ring-error"/>
          <span class="text-xs sm:text-sm font-semibold text-error">Delete all photos in inventory</span>
        </div>
        <span id="del-count-all" class="text-xs font-bold text-error">All</span>
      </label>
    </div>

    <!-- Red Destructive Button and Cancel -->
    <div class="flex flex-col sm:flex-row gap-2.5 pt-1">
      <button type="button" onclick="closeDeleteModal()"
              class="flex-1 py-3.5 rounded-2xl bg-surface-container hover:bg-surface-container-high text-on-surface font-semibold text-sm transition-all">
        Cancel
      </button>
      <button type="button" onclick="confirmExecuteDelete()" id="btn-confirm-destructive-delete"
              class="flex-1 py-3.5 rounded-2xl bg-error hover:opacity-95 text-white font-semibold text-sm shadow-md shadow-error/20 transition-all">
        Delete Items
      </button>
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- MOBILE BOTTOM TAB BAR (3 TABS: UPLOAD, GALLERY, FRAMES)                   -->
<!-- ========================================================================= -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 z-40 apple-glass border-t border-outline-variant/30 px-6 py-2 flex items-center justify-around">
  <button type="button" onclick="switchTab('upload')" id="nav-mob-upload" class="flex flex-col items-center gap-0.5 py-1 text-primary font-semibold">
    <span class="material-symbols-outlined text-[24px]">cloud_upload</span>
    <span class="text-[11px]">Upload</span>
  </button>
  <button type="button" onclick="switchTab('gallery')" id="nav-mob-gallery" class="flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium">
    <span class="material-symbols-outlined text-[24px]">photo_library</span>
    <span class="text-[11px]">Gallery</span>
  </button>
  <button type="button" onclick="switchTab('frames')" id="nav-mob-frames" class="flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium">
    <span class="material-symbols-outlined text-[24px]">crop_free</span>
    <span class="text-[11px]">Frames</span>
  </button>
</nav>

<script>
  // Application State
  let appState = {
    cars_output: {},
    cars_review: {},
    cars_meta: {}
  };
  let activeTab = 'upload';
  let uploadFilesQueue = [];
  let uploadRatio = '16:9';

  // Gallery & Selection State
  let galleryFilter = 'all';
  let globalCompareMode = 'after'; // 'after' (Plate Removed) or 'before' (Original)
  let cardCompareModes = {};       // per-car override: {car_id: 'after' | 'before'}
  let selectionMode = false;
  let selectedPhotoKeys = new Set(); // "car_id::filename"
  let selectedCarIds = new Set();    // "car_id"
  let activeModalCarId = null;
  let modalCompareMode = 'after';
  let pendingDeleteTargetCarId = null;

  // Frame Studio State
  let studioCarId = null;
  let studioFilename = null;
  let studioRatio = '1:1';
  let studioFitMode = 'fit'; // 'fit' (blurred photo bg) or 'fill' (crop + pan)
  let studioTemplate = 'clean_white';
  let studioOffsetX = 0.5;
  let studioOffsetY = 0.5;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;
  let studioDebounceTimer = null;

  const SAMPLE_PLATES = ['SXX 1234 A', 'SBA 8888 X', 'SGP 9110 T', 'SLR 4580 M', 'SKL 2026 Z'];

  // Switch between the 3 primary tabs: Upload, Gallery, Frames
  function switchTab(tab) {
    activeTab = tab;
    ['upload', 'gallery', 'frames'].forEach(t => {
      const sec = document.getElementById('screen-' + t);
      if (sec) sec.classList.toggle('hidden', t !== tab);

      const deskBtn = document.getElementById('nav-desk-' + t);
      if (deskBtn) {
        if (t === tab) {
          deskBtn.className = 'px-5 py-1.5 rounded-full text-sm font-semibold transition-all flex items-center gap-1.5 bg-white text-primary shadow-sm';
        } else {
          deskBtn.className = 'px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
        }
      }

      const mobBtn = document.getElementById('nav-mob-' + t);
      if (mobBtn) {
        mobBtn.className = (t === tab)
          ? 'flex flex-col items-center gap-0.5 py-1 text-primary font-semibold'
          : 'flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium';
      }
    });

    if (tab !== 'gallery') {
      document.getElementById('selection-floating-bar').classList.add('hidden');
    } else {
      updateSelectionBar();
      renderGallery();
    }

    if (tab === 'frames') {
      populateFrameStudioSelectors();
      refreshStudioCanvas();
    }
  }

  // Fetch backend state
  async function fetchState() {
    try {
      const res = await fetch('/api/state', { credentials: 'same-origin' });
      if (!res.ok) return;
      appState = await res.json();
      if (appState.frame_config) {
        syncUiWithFrameConfig(appState.frame_config);
      }
      updateGalleryCountBadge();
      renderGallery();
      populateFrameStudioSelectors();
    } catch (err) {
      console.error('Error loading state:', err);
    }
  }

  function syncUiWithFrameConfig(fcfg) {
    if (!fcfg) return;
    studioRatio = fcfg.ratio || studioRatio;
    uploadRatio = fcfg.ratio || uploadRatio;
    studioFitMode = fcfg.fit_mode || studioFitMode;
    studioTemplate = fcfg.template_style || studioTemplate;
    studioOffsetX = typeof fcfg.offset_x === 'number' ? fcfg.offset_x : studioOffsetX;
    studioOffsetY = typeof fcfg.offset_y === 'number' ? fcfg.offset_y : studioOffsetY;

    // Update Upload ratio buttons
    ['1:1', '16:9', '9:16'].forEach(r => {
      const btn = document.getElementById('up-ratio-' + r);
      if (btn) {
        btn.className = (r === uploadRatio)
          ? 'py-2 rounded-xl text-xs font-bold bg-white text-primary shadow-sm transition-all'
          : 'py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      }
      const stBtn = document.getElementById('st-ratio-' + r);
      if (stBtn) {
        stBtn.className = (r === studioRatio)
          ? 'px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all'
          : 'px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      }
    });

    // Update Fit/Fill buttons
    const fitBtn = document.getElementById('st-fit-fit');
    const fillBtn = document.getElementById('st-fit-fill');
    if (fitBtn && fillBtn) {
      fitBtn.className = (studioFitMode === 'fit')
        ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
        : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
      fillBtn.className = (studioFitMode === 'fill')
        ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
        : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
    }

    // Update Template cards
    const tplLbl = document.getElementById('studio-active-template-label');
    if (tplLbl) tplLbl.textContent = TEMPLATE_LABELS[studioTemplate] || studioTemplate;
    Object.keys(TEMPLATE_LABELS).forEach(k => {
      const b = document.getElementById('tpl-' + k);
      if (b) {
        b.className = (k === studioTemplate)
          ? 'p-3 rounded-2xl border-2 border-primary bg-primary-fixed/15 text-left transition-all'
          : 'p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all';
      }
    });

    const capToggle = document.getElementById('studio-caption-toggle');
    if (capToggle && typeof fcfg.caption_enabled === 'boolean') {
      capToggle.checked = fcfg.caption_enabled;
    }

    const presetPill = document.getElementById('upload-active-preset-pill');
    if (presetPill) {
      const tName = TEMPLATE_LABELS[studioTemplate] || 'Clean White';
      const fName = studioFitMode === 'fill' ? 'Fill' : 'Fit (Blur)';
      presetPill.textContent = `${tName} • ${fName} • ${studioRatio}`;
    }

    const ovBadge = document.getElementById('overlay-status-badge');
    if (ovBadge) {
      ovBadge.textContent = fcfg.has_custom_overlay ? 'Custom Cover' : 'Default Cover';
    }
  }

  function getAllCarIds() {
    const outKeys = Object.keys(appState.cars_output || {});
    const revKeys = Object.keys(appState.cars_review || {});
    return Array.from(new Set([...outKeys, ...revKeys])).sort();
  }

  function getCarPhotos(carId) {
    const outList = (appState.cars_output && appState.cars_output[carId]) || [];
    const revList = (appState.cars_review && appState.cars_review[carId]) || [];
    return [...outList, ...revList];
  }

  function getCarMeta(carId) {
    const meta = (appState.cars_meta && appState.cars_meta[carId]) || {};
    return {
      plate_display: meta.plate_display || carId.replace(/-/g, ' '),
      car_model: meta.car_model || 'Forest Wheel Showroom Vehicle',
      car_price: meta.car_price || '$188,800',
      car_specs: meta.car_specs || 'Verified Pre-Owned • Singapore'
    };
  }

  function updateGalleryCountBadge() {
    const cids = getAllCarIds();
    const badge = document.getElementById('badge-desk-gallery');
    if (badge) badge.textContent = String(cids.length);
  }

  // =========================================================================
  // SCREEN 1: UPLOAD & PROGRESS RING LOGIC
  // =========================================================================
  function setUploadRatio(ratio) {
    uploadRatio = ratio;
    ['1:1', '16:9', '9:16'].forEach(r => {
      const btn = document.getElementById('up-ratio-' + r);
      if (!btn) return;
      btn.className = (r === ratio)
        ? 'py-2 rounded-xl text-xs font-bold bg-white text-primary shadow-sm transition-all'
        : 'py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    });
  }

  function handleFilesSelected(fileList) {
    if (!fileList || !fileList.length) return;
    const arr = Array.from(fileList);
    arr.forEach((file, idx) => {
      const objUrl = URL.createObjectURL(file);
      uploadFilesQueue.push({
        file: file,
        name: file.name,
        previewUrl: objUrl,
        stage: 'detecting', // 'detecting' -> 'removing' -> 'ready' | 'done'
        progress: 38
      });
    });

    // Auto-fill Plate number if still default or empty
    const plateInput = document.getElementById('input-plate-number');
    if (plateInput && (!plateInput.value.trim() || plateInput.value === 'SXX 1234 A')) {
      const pick = SAMPLE_PLATES[Math.floor(Math.random() * SAMPLE_PLATES.length)];
      plateInput.value = pick;
    }

    renderUploadQueue();

    // Animate simulated plate detection pre-scan ring (Detecting plate -> Ready to remove)
    setTimeout(() => {
      uploadFilesQueue.forEach(item => {
        if (item.stage === 'detecting') {
          item.stage = 'removing';
          item.progress = 76;
        }
      });
      renderUploadQueue();
    }, 450);

    setTimeout(() => {
      uploadFilesQueue.forEach(item => {
        if (item.stage === 'removing') {
          item.stage = 'detected';
          item.progress = 100;
        }
      });
      renderUploadQueue();
    }, 950);
  }

  function clearUploadQueue() {
    uploadFilesQueue = [];
    renderUploadQueue();
  }

  function removeQueuedFile(idx) {
    uploadFilesQueue.splice(idx, 1);
    renderUploadQueue();
  }

  function renderUploadQueue() {
    const grid = document.getElementById('upload-thumbnails-grid');
    const badge = document.getElementById('upload-queue-badge');
    if (badge) badge.textContent = `${uploadFilesQueue.length} Photo${uploadFilesQueue.length === 1 ? '' : 's'}`;
    if (!grid) return;

    if (uploadFilesQueue.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full apple-card-white rounded-2xl p-6 text-center text-xs text-on-surface-variant">
          No photos queued yet. Click <strong>Upload photos</strong> above or load sample cars to test.
        </div>`;
      return;
    }

    const circumference = 2 * Math.PI * 18;
    grid.innerHTML = uploadFilesQueue.map((item, idx) => {
      const offset = circumference - (item.progress / 100) * circumference;
      let statusBadge = '';
      if (item.stage === 'detecting') {
        statusBadge = `
          <div class="apple-glass px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
            <svg class="w-5 h-5 spin-ring" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="#d8e2ff" stroke-width="4"/>
              <circle cx="22" cy="22" r="18" fill="none" stroke="#0058bc" stroke-width="4" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
            </svg>
            <span class="text-[11px] font-bold text-on-surface">Detecting plate…</span>
          </div>`;
      } else if (item.stage === 'removing') {
        statusBadge = `
          <div class="apple-glass px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
            <svg class="w-5 h-5 spin-ring" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="#d8e2ff" stroke-width="4"/>
              <circle cx="22" cy="22" r="18" fill="none" stroke="#0070eb" stroke-width="4" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
            </svg>
            <span class="text-[11px] font-bold text-primary">Removing plate…</span>
          </div>`;
      } else {
        statusBadge = `
          <div class="bg-emerald-600/95 text-white px-3 py-1 rounded-full flex items-center gap-1.5 shadow-sm">
            <span class="material-symbols-outlined text-[15px] material-fill">check_circle</span>
            <span class="text-[11px] font-bold">${item.stage === 'done' ? 'Done' : 'Plate Detected'}</span>
          </div>`;
      }

      return `
        <div class="group relative aspect-[4/3] rounded-2xl overflow-hidden bg-surface-container border border-outline-variant/30 shadow-sm">
          <img src="${item.previewUrl}" alt="${item.name}" class="w-full h-full object-cover"/>
          <div class="absolute inset-0 bg-black/15 flex items-center justify-center">
            ${statusBadge}
          </div>
          <button type="button" onclick="removeQueuedFile(${idx})" class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <span class="material-symbols-outlined text-[16px]">close</span>
          </button>
          <div class="absolute bottom-2 left-2 right-2 px-2.5 py-1 rounded-lg bg-black/45 backdrop-blur-xs text-white text-[10px] font-medium truncate">
            ${item.name}
          </div>
        </div>
      `;
    }).join('');
  }

  async function submitUploadBatch() {
    const plateVal = (document.getElementById('input-plate-number').value || 'SXX 1234 A').trim();
    const modelVal = (document.getElementById('input-car-model').value || '').trim();
    const priceVal = (document.getElementById('input-car-price').value || '').trim();
    const msgEl = document.getElementById('upload-status-msg');
    const btnLabel = document.getElementById('btn-process-save-label');

    if (uploadFilesQueue.length === 0) {
      msgEl.textContent = 'No local files selected — loading sample showroom batch for ' + plateVal + '…';
      await runDemoBatch(plateVal);
      return;
    }

    // Mark all items as "Removing plate…" during server processing
    uploadFilesQueue.forEach(item => { item.stage = 'removing'; item.progress = 82; });
    renderUploadQueue();
    btnLabel.textContent = 'Processing Plates…';

    const fd = new FormData();
    fd.append('car_id', plateVal);
    fd.append('ratio', uploadRatio);
    fd.append('car_model', modelVal);
    fd.append('car_price', priceVal);
    uploadFilesQueue.forEach(item => fd.append('files', item.file));

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: fd,
        credentials: 'same-origin'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      uploadFilesQueue.forEach(item => { item.stage = 'done'; item.progress = 100; });
      renderUploadQueue();
      btnLabel.textContent = 'Process & Save';
      msgEl.textContent = `Processed ${data.processed_count} photos for ${plateVal} (${data.output_count} ready, ${data.review_count} in review).`;

      await fetchState();
      setTimeout(() => {
        clearUploadQueue();
        switchTab('gallery');
      }, 650);
    } catch (err) {
      btnLabel.textContent = 'Process & Save';
      msgEl.textContent = 'Error: ' + err.message;
    }
  }

  async function runDemoBatch(customPlate) {
    const plate = customPlate || document.getElementById('input-plate-number').value || 'SXX-1234-A';
    const btn = document.getElementById('btn-demo-load');
    if (btn) btn.disabled = true;
    try {
      const res = await fetch(`/api/demo-batch?car_id=${encodeURIComponent(plate)}&ratio=${encodeURIComponent(uploadRatio)}`, {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (res.ok) {
        await fetchState();
        switchTab('gallery');
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // =========================================================================
  // SCREEN 2: VEHICLE GALLERY (GROUPED BY PLATE NUMBER) & BEFORE/AFTER TOGGLE
  // =========================================================================
  function setGalleryFilter(flt) {
    galleryFilter = flt;
    ['all', 'ready', 'review'].forEach(k => {
      const b = document.getElementById('flt-' + k);
      if (!b) return;
      b.className = (k === flt)
        ? 'px-4 py-1.5 rounded-full text-xs font-semibold bg-on-surface text-white transition-all'
        : 'px-4 py-1.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant hover:text-on-surface transition-all';
    });
    renderGallery();
  }

  function setGlobalCompareMode(mode) {
    globalCompareMode = mode;
    cardCompareModes = {};
    document.getElementById('btn-global-after').className = (mode === 'after')
      ? 'px-3.5 py-1 rounded-full text-xs font-semibold bg-white text-primary shadow-sm transition-all'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    document.getElementById('btn-global-before').className = (mode === 'before')
      ? 'px-3.5 py-1 rounded-full text-xs font-semibold bg-white text-primary shadow-sm transition-all'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    renderGallery();
  }

  function toggleCardCompareMode(carId, mode, ev) {
    if (ev) ev.stopPropagation();
    cardCompareModes[carId] = mode;
    renderGallery();
  }

  function getMediaUrlForPhoto(carId, photoObj, compareMode, fullRes = false) {
    const fn = encodeURIComponent(photoObj.filename);
    const cid = encodeURIComponent(carId);
    const fullParam = fullRes ? '&full=1' : '';
    const activeRatio = encodeURIComponent(studioRatio || uploadRatio || '16:9');
    if (compareMode === 'before') {
      return `/media/original/${cid}/${fn}?full=${fullRes ? 1 : 0}`;
    }
    if (photoObj.status === 'ready') {
      return `/media/output/${cid}/${fn}?ratio=${activeRatio}${fullParam}`;
    }
    return `/media/after/${cid}/${fn}?ratio=${activeRatio}${fullParam}`;
  }

  function openPhotoFullWindow(carId, filename, status, compareMode, ev) {
    if (ev) ev.stopPropagation();
    const url = getMediaUrlForPhoto(carId, { filename: filename, status: status }, compareMode, true);
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function renderGallery() {
    const container = document.getElementById('gallery-cards-container');
    if (!container) return;

    const query = (document.getElementById('gallery-search-input')?.value || '').trim().toLowerCase();
    const carIds = getAllCarIds().filter(cid => {
      const meta = getCarMeta(cid);
      const photos = getCarPhotos(cid);
      if (photos.length === 0) return false;
      if (galleryFilter === 'ready' && !photos.some(p => p.status === 'ready')) return false;
      if (galleryFilter === 'review' && !photos.some(p => p.status !== 'ready')) return false;
      if (!query) return true;
      return cid.toLowerCase().includes(query) ||
             meta.plate_display.toLowerCase().includes(query) ||
             meta.car_model.toLowerCase().includes(query);
    });

    if (carIds.length === 0) {
      container.innerHTML = `
        <div class="col-span-full apple-card-white rounded-[28px] p-12 text-center space-y-4">
          <div class="w-14 h-14 rounded-2xl bg-surface-container mx-auto flex items-center justify-center text-outline">
            <span class="material-symbols-outlined text-3xl">directions_car</span>
          </div>
          <div>
            <h3 class="text-lg font-bold text-on-surface">No vehicles found</h3>
            <p class="text-xs sm:text-sm text-on-surface-variant mt-1">Upload car photos in the Upload tab or load sample cars to populate the gallery.</p>
          </div>
          <button type="button" onclick="runDemoBatch('SXX-1234-A')" class="px-5 py-2.5 rounded-full bg-primary text-white text-xs font-semibold shadow-sm">
            Load Sample Showroom Batch
          </button>
        </div>`;
      return;
    }

    container.innerHTML = carIds.map(cid => {
      const meta = getCarMeta(cid);
      const photos = getCarPhotos(cid);
      const mode = cardCompareModes[cid] || globalCompareMode;
      const previewPhotos = photos.slice(0, 4);
      const isCarSelected = selectedCarIds.has(cid);
      const readyCount = photos.filter(p => p.status === 'ready').length;
      const reviewCount = photos.length - readyCount;

      const thumbsHtml = previewPhotos.map(p => {
        const key = `${cid}::${p.filename}`;
        const isSelected = selectedPhotoKeys.has(key) || isCarSelected;
        const imgUrl = getMediaUrlForPhoto(cid, p, mode);

        return `
          <div onclick="onGalleryThumbClick('${cid}', '${p.filename}', event)"
               class="relative aspect-[4/3] rounded-2xl overflow-hidden bg-surface-container border ${isSelected ? 'border-primary ring-2 ring-primary' : 'border-outline-variant/25'} cursor-pointer group">
            <img src="${imgUrl}" alt="${p.filename}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>
            <div class="absolute bottom-1.5 left-1.5 px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider ${mode === 'before' ? 'bg-amber-500/90 text-white' : 'bg-black/55 text-white'}">
              ${mode === 'before' ? 'Original' : 'Plate Removed'}
            </div>
            ${selectionMode ? `
              <div class="absolute top-2 right-2 w-6 h-6 rounded-full ${isSelected ? 'bg-primary text-white' : 'bg-white/85 text-transparent border border-outline-variant'} flex items-center justify-center shadow-sm">
                <span class="material-symbols-outlined text-[16px] material-fill">check</span>
              </div>
            ` : ''}
          </div>
        `;
      }).join('');

      return `
        <div onclick="onCarCardClick('${cid}', event)"
             class="apple-card-white rounded-[26px] p-5 sm:p-6 transition-all hover:shadow-apple-float cursor-pointer ${isCarSelected ? 'ring-2 ring-primary bg-primary-fixed/10' : ''}">
          <!-- Card Top Row: Plate Number Title + Photo Count + Before/After Toggle -->
          <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div class="flex items-center gap-3">
              ${selectionMode ? `
                <button type="button" onclick="toggleSelectCarGroup('${cid}', event)"
                        class="w-7 h-7 rounded-full ${isCarSelected ? 'bg-primary text-white' : 'bg-surface-container border border-outline-variant text-transparent'} flex items-center justify-center transition-all">
                  <span class="material-symbols-outlined text-[18px] material-fill">check</span>
                </button>
              ` : ''}
              <div>
                <div class="flex items-center gap-2">
                  <span class="px-3 py-1 rounded-xl bg-primary-fixed text-primary font-extrabold text-sm tracking-wider uppercase">${meta.plate_display}</span>
                  <span class="text-xs font-semibold text-on-surface-variant">${photos.length} photo${photos.length === 1 ? '' : 's'}</span>
                  ${reviewCount > 0 ? `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">${reviewCount} Review</span>` : ''}
                </div>
                <h3 class="text-base font-bold text-on-surface mt-1.5">${meta.car_model}</h3>
              </div>
            </div>

            <!-- Card-Level Before / After Segmented Toggle -->
            <div class="flex items-center gap-1.5" onclick="event.stopPropagation()">
              <div class="inline-flex bg-surface-container p-0.5 rounded-full border border-outline-variant/25">
                <button type="button" onclick="toggleCardCompareMode('${cid}', 'after', event)"
                        class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${mode === 'after' ? 'bg-white text-primary shadow-xs' : 'text-on-surface-variant'}">
                  Clean
                </button>
                <button type="button" onclick="toggleCardCompareMode('${cid}', 'before', event)"
                        class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${mode === 'before' ? 'bg-white text-primary shadow-xs' : 'text-on-surface-variant'}">
                  Original
                </button>
              </div>

              <!-- Quick Delete Car Group Button -->
              <button type="button" onclick="openDeleteModal('car', '${cid}', event)"
                      class="w-8 h-8 rounded-full hover:bg-error-container/50 text-on-surface-variant hover:text-error flex items-center justify-center transition-colors"
                      title="Delete entire car group">
                <span class="material-symbols-outlined text-[18px]">delete</span>
              </button>
            </div>
          </div>

          <!-- Horizontal Strip / Grid of 3-4 Preview Thumbnails -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
            ${thumbsHtml}
          </div>

          <!-- Card Footer Actions -->
          <div class="flex items-center justify-between pt-3 border-t border-surface-container text-xs font-semibold">
            <span class="text-primary flex items-center gap-1">
              <span>Tap to view all ${photos.length} photos</span>
              <span class="material-symbols-outlined text-[15px]">chevron_right</span>
            </span>
            <div class="flex items-center gap-3" onclick="event.stopPropagation()">
              <button type="button" onclick="openCarInFrames('${cid}')" class="text-on-surface-variant hover:text-primary flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">crop_free</span>
                <span>Frame Studio</span>
              </button>
              <a href="/api/export/${encodeURIComponent(cid)}?ratio=16:9" class="text-on-surface-variant hover:text-primary flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">download</span>
                <span>ZIP</span>
              </a>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function onCarCardClick(carId, ev) {
    if (selectionMode) {
      toggleSelectCarGroup(carId, ev);
      return;
    }
    openCarDetailModal(carId);
  }

  function onGalleryThumbClick(carId, filename, ev) {
    if (ev) ev.stopPropagation();
    if (selectionMode) {
      const key = `${carId}::${filename}`;
      if (selectedPhotoKeys.has(key)) {
        selectedPhotoKeys.delete(key);
        selectedCarIds.delete(carId);
      } else {
        selectedPhotoKeys.add(key);
      }
      updateSelectionBar();
      renderGallery();
      return;
    }
    const photos = getCarPhotos(carId);
    const pObj = photos.find(p => p.filename === filename) || { filename: filename, status: 'ready' };
    const mode = cardCompareModes[carId] || globalCompareMode;
    openPhotoFullWindow(carId, filename, pObj.status, mode, ev);
  }

  // =========================================================================
  // CAR DETAIL MODAL (ALL PHOTOS FOR THAT CAR + BEFORE/AFTER + EDIT/DELETE)
  // =========================================================================
  function openCarDetailModal(carId) {
    activeModalCarId = carId;
    modalCompareMode = cardCompareModes[carId] || globalCompareMode;
    document.getElementById('modal-edit-car-drawer').classList.add('hidden');
    document.getElementById('car-detail-modal').classList.remove('hidden');
    renderCarDetailModal();
  }

  function closeCarDetailModal() {
    document.getElementById('car-detail-modal').classList.add('hidden');
    activeModalCarId = null;
  }

  function setModalCompareMode(mode) {
    modalCompareMode = mode;
    document.getElementById('modal-btn-after').className = (mode === 'after')
      ? 'px-3.5 py-1 rounded-full text-xs font-bold bg-white text-primary shadow-sm'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant';
    document.getElementById('modal-btn-before').className = (mode === 'before')
      ? 'px-3.5 py-1 rounded-full text-xs font-bold bg-white text-primary shadow-sm'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant';
    renderCarDetailModal();
  }

  function toggleEditCarGroupForm() {
    if (!activeModalCarId) return;
    const drawer = document.getElementById('modal-edit-car-drawer');
    const meta = getCarMeta(activeModalCarId);
    document.getElementById('edit-car-plate').value = meta.plate_display;
    document.getElementById('edit-car-model').value = meta.car_model;
    document.getElementById('edit-car-price').value = meta.car_price;
    drawer.classList.toggle('hidden');
  }

  async function saveCarGroupMetadata() {
    if (!activeModalCarId) return;
    const newPlate = document.getElementById('edit-car-plate').value.trim();
    const newModel = document.getElementById('edit-car-model').value.trim();
    const newPrice = document.getElementById('edit-car-price').value.trim();

    const res = await fetch(`/api/cars/${encodeURIComponent(activeModalCarId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        new_car_id: newPlate,
        plate_display: newPlate,
        car_model: newModel,
        car_price: newPrice
      })
    });
    if (res.ok) {
      const data = await res.json();
      activeModalCarId = data.car_id;
      document.getElementById('modal-edit-car-drawer').classList.add('hidden');
      await fetchState();
      renderCarDetailModal();
    }
  }

  function renderCarDetailModal() {
    if (!activeModalCarId) return;
    const meta = getCarMeta(activeModalCarId);
    const photos = getCarPhotos(activeModalCarId);

    document.getElementById('modal-car-plate-badge').textContent = meta.plate_display;
    document.getElementById('modal-car-title').textContent = meta.car_model;
    document.getElementById('modal-car-count').textContent = `${photos.length} photo${photos.length === 1 ? '' : 's'} • ${meta.car_price}`;

    const grid = document.getElementById('modal-photos-grid');
    if (photos.length === 0) {
      closeCarDetailModal();
      return;
    }

    grid.innerHTML = photos.map(p => {
      const imgUrl = getMediaUrlForPhoto(activeModalCarId, p, modalCompareMode);
      const isReview = p.status !== 'ready';
      return `
        <div class="apple-card-white rounded-2xl overflow-hidden flex flex-col justify-between border border-outline-variant/30">
          <div onclick="openPhotoFullWindow('${activeModalCarId}', '${p.filename}', '${p.status}', '${modalCompareMode}', event)"
               class="relative aspect-[4/3] bg-surface-container cursor-zoom-in group" title="Click to open full image in new window">
            <img src="${imgUrl}" alt="${p.filename}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>
            <span class="absolute top-2.5 left-2.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${modalCompareMode === 'before' ? 'bg-amber-500 text-white' : 'bg-emerald-600 text-white'}">
              ${modalCompareMode === 'before' ? 'Original' : 'Plate Removed'}
            </span>
            <button type="button" onclick="event.stopPropagation(); deleteSinglePhoto('${activeModalCarId}', '${p.filename}')"
                    class="absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-white/90 hover:bg-error hover:text-white text-error flex items-center justify-center shadow-sm transition-colors"
                    title="Delete this photo">
              <span class="material-symbols-outlined text-[18px]">delete</span>
            </button>
          </div>
          <div class="p-3.5 flex items-center justify-between gap-2">
            <div class="truncate">
              <p class="text-xs font-bold text-on-surface truncate">${p.filename}</p>
              <p class="text-[10px] text-on-surface-variant">${isReview ? 'Needs review: ' + p.reason : 'Plate masked & verified'}</p>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              ${isReview ? `
                <button type="button" onclick="approveReviewPhoto('${activeModalCarId}', '${p.filename}')" class="px-2.5 py-1 rounded-lg bg-emerald-600 text-white text-[11px] font-semibold">Approve</button>
              ` : ''}
              <button type="button" onclick="closeCarDetailModal(); openPhotoInFrames('${activeModalCarId}', '${p.filename}')"
                      class="px-3 py-1.5 rounded-xl bg-primary-fixed text-primary text-xs font-semibold hover:bg-primary hover:text-white transition-colors">
                Frame
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  async function approveReviewPhoto(carId, filename) {
    const res = await fetch(`/api/approve/${encodeURIComponent(carId)}/${encodeURIComponent(filename)}`, {
      method: 'POST',
      credentials: 'same-origin'
    });
    if (res.ok) {
      await fetchState();
      if (activeModalCarId) renderCarDetailModal();
    }
  }

  async function deleteSinglePhoto(carId, filename) {
    const res = await fetch('/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        scope: 'selected',
        items: [{ car_id: carId, filename: filename }]
      })
    });
    if (res.ok) {
      await fetchState();
      if (activeModalCarId) renderCarDetailModal();
    }
  }

  // =========================================================================
  // SCREEN 4: SELECTION MODE & DELETE CONFIRMATION MODAL
  // =========================================================================
  function toggleSelectionMode() {
    selectionMode = !selectionMode;
    const btn = document.getElementById('btn-toggle-select-mode');
    const lbl = document.getElementById('label-select-mode');
    if (selectionMode) {
      btn.className = 'px-5 py-2.5 rounded-full font-semibold text-sm bg-primary text-white transition-all flex items-center gap-1.5 shadow-sm';
      lbl.textContent = 'Done';
    } else {
      btn.className = 'px-5 py-2.5 rounded-full font-semibold text-sm border border-outline-variant/50 bg-white hover:bg-surface-container-low text-on-surface transition-all flex items-center gap-1.5 shadow-sm';
      lbl.textContent = 'Select';
      selectedPhotoKeys.clear();
      selectedCarIds.clear();
    }
    updateSelectionBar();
    renderGallery();
  }

  function toggleSelectCarGroup(carId, ev) {
    if (ev) ev.stopPropagation();
    const photos = getCarPhotos(carId);
    if (selectedCarIds.has(carId)) {
      selectedCarIds.delete(carId);
      photos.forEach(p => selectedPhotoKeys.delete(`${carId}::${p.filename}`));
    } else {
      selectedCarIds.add(carId);
      photos.forEach(p => selectedPhotoKeys.add(`${carId}::${p.filename}`));
    }
    updateSelectionBar();
    renderGallery();
  }

  function selectAllGalleryItems() {
    getAllCarIds().forEach(cid => {
      selectedCarIds.add(cid);
      getCarPhotos(cid).forEach(p => selectedPhotoKeys.add(`${cid}::${p.filename}`));
    });
    updateSelectionBar();
    renderGallery();
  }

  function clearAllSelections() {
    selectedPhotoKeys.clear();
    selectedCarIds.clear();
    updateSelectionBar();
    renderGallery();
  }

  function updateSelectionBar() {
    const bar = document.getElementById('selection-floating-bar');
    if (!bar) return;
    const count = selectedPhotoKeys.size;
    if (selectionMode && activeTab === 'gallery') {
      bar.classList.remove('hidden');
      document.getElementById('selection-counter-pill').textContent = `${count} selected`;
      document.getElementById('btn-floating-delete-label').textContent = `Delete Selected (${count})`;
    } else {
      bar.classList.add('hidden');
    }
  }

  function openDeleteModal(defaultScope, targetCarId, ev) {
    if (ev) ev.stopPropagation();
    pendingDeleteTargetCarId = targetCarId || activeModalCarId || Array.from(selectedCarIds)[0] || getAllCarIds()[0] || null;

    const radios = document.querySelectorAll('input[name="delete-scope-radio"]');
    radios.forEach(r => { r.checked = (r.value === defaultScope); });

    const totalInventoryPhotos = getAllCarIds().reduce((acc, cid) => acc + getCarPhotos(cid).length, 0);
    const selCount = selectedPhotoKeys.size;
    const carGroupCount = selectedCarIds.size > 0
      ? selectedCarIds.size
      : (pendingDeleteTargetCarId ? 1 : 0);

    document.getElementById('del-count-selected').textContent = `${selCount} photo${selCount === 1 ? '' : 's'}`;
    document.getElementById('del-count-car').textContent = pendingDeleteTargetCarId
      ? `${pendingDeleteTargetCarId} (${getCarPhotos(pendingDeleteTargetCarId).length} photos)`
      : `${carGroupCount} group`;
    document.getElementById('del-count-all').textContent = `${totalInventoryPhotos} photos`;

    updateDeleteModalSummary();
    document.getElementById('delete-confirm-modal').classList.remove('hidden');
  }

  function updateDeleteModalSummary() {
    const chosen = document.querySelector('input[name="delete-scope-radio"]:checked')?.value || 'selected';
    const btn = document.getElementById('btn-confirm-destructive-delete');
    const totalInventoryPhotos = getAllCarIds().reduce((acc, cid) => acc + getCarPhotos(cid).length, 0);

    if (chosen === 'all') {
      btn.textContent = `Delete All (${totalInventoryPhotos} Photos)`;
    } else if (chosen === 'car') {
      const cids = selectedCarIds.size > 0 ? Array.from(selectedCarIds) : (pendingDeleteTargetCarId ? [pendingDeleteTargetCarId] : []);
      btn.textContent = `Delete Car Group (${cids.join(', ') || '1 Group'})`;
    } else {
      btn.textContent = `Delete Selected (${selectedPhotoKeys.size})`;
    }
  }

  function closeDeleteModal() {
    document.getElementById('delete-confirm-modal').classList.add('hidden');
  }

  async function confirmExecuteDelete() {
    const chosen = document.querySelector('input[name="delete-scope-radio"]:checked')?.value || 'selected';
    let payload = { scope: chosen };

    if (chosen === 'car') {
      const cids = selectedCarIds.size > 0
        ? Array.from(selectedCarIds)
        : (pendingDeleteTargetCarId ? [pendingDeleteTargetCarId] : []);
      payload.car_ids = cids;
    } else if (chosen === 'selected') {
      payload.items = Array.from(selectedPhotoKeys).map(k => {
        const [cid, fn] = k.split('::');
        return { car_id: cid, filename: fn };
      });
    }

    const res = await fetch('/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      selectedPhotoKeys.clear();
      selectedCarIds.clear();
      closeDeleteModal();
      closeCarDetailModal();
      if (selectionMode) toggleSelectionMode();
      await fetchState();
    }
  }

  // =========================================================================
  // SCREEN 3: FRAME TEMPLATE EDITOR (1:1, 16:9, 9:16 + FIT/FILL + 5 TEMPLATES)
  // =========================================================================
  function openCarInFrames(carId) {
    studioCarId = carId;
    const photos = getCarPhotos(carId);
    studioFilename = photos.length > 0 ? photos[0].filename : null;
    const meta = getCarMeta(carId);
    document.getElementById('studio-model-input').value = meta.car_model;
    document.getElementById('studio-price-input').value = meta.car_price;
    switchTab('frames');
  }

  function openPhotoInFrames(carId, filename) {
    studioCarId = carId;
    studioFilename = filename;
    const meta = getCarMeta(carId);
    document.getElementById('studio-model-input').value = meta.car_model;
    document.getElementById('studio-price-input').value = meta.car_price;
    switchTab('frames');
  }

  function populateFrameStudioSelectors() {
    const sel = document.getElementById('frame-car-select');
    if (!sel) return;
    const cids = getAllCarIds();
    if (cids.length === 0) {
      sel.innerHTML = `<option value="">Sample Showroom Car</option>`;
      return;
    }
    if (!studioCarId || !cids.includes(studioCarId)) {
      studioCarId = cids[0];
    }
    sel.innerHTML = cids.map(cid => {
      const meta = getCarMeta(cid);
      return `<option value="${cid}" ${cid === studioCarId ? 'selected' : ''}>${meta.plate_display} — ${meta.car_model}</option>`;
    }).join('');

    renderFramePhotoStrip();
  }

  function onFrameCarChange() {
    const sel = document.getElementById('frame-car-select');
    studioCarId = sel.value;
    const photos = getCarPhotos(studioCarId);
    studioFilename = photos.length > 0 ? photos[0].filename : null;
    const meta = getCarMeta(studioCarId);
    document.getElementById('studio-model-input').value = meta.car_model;
    document.getElementById('studio-price-input').value = meta.car_price;
    renderFramePhotoStrip();
    refreshStudioCanvas();
  }

  function renderFramePhotoStrip() {
    const strip = document.getElementById('frame-photo-strip');
    if (!strip || !studioCarId) return;
    const photos = getCarPhotos(studioCarId);
    if (!studioFilename && photos.length > 0) {
      studioFilename = photos[0].filename;
    }
    strip.innerHTML = photos.map(p => {
      const active = p.filename === studioFilename;
      const thumbUrl = getMediaUrlForPhoto(studioCarId, p, 'after');
      return `
        <button type="button" onclick="selectStudioPhoto('${p.filename}')"
                class="relative aspect-square rounded-xl overflow-hidden border-2 ${active ? 'border-primary ring-2 ring-primary/30' : 'border-transparent opacity-75 hover:opacity-100'} transition-all">
          <img src="${thumbUrl}" alt="${p.filename}" class="w-full h-full object-cover"/>
        </button>
      `;
    }).join('');
  }

  function selectStudioPhoto(fn) {
    studioFilename = fn;
    renderFramePhotoStrip();
    refreshStudioCanvas();
  }

  function setStudioRatio(r) {
    studioRatio = r;
    uploadRatio = r;
    ['1:1', '16:9', '9:16'].forEach(k => {
      const b = document.getElementById('st-ratio-' + k);
      if (b) {
        b.className = (k === r)
          ? 'px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all'
          : 'px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      }
    });
    refreshStudioCanvas();
    saveGlobalFramePreset(true);
  }

  function setStudioFitMode(mode) {
    studioFitMode = mode;
    document.getElementById('st-fit-fit').className = (mode === 'fit')
      ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
      : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
    document.getElementById('st-fit-fill').className = (mode === 'fill')
      ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
      : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';

    document.getElementById('studio-pan-hint').classList.toggle('hidden', mode !== 'fill');
    refreshStudioCanvas();
    saveGlobalFramePreset(true);
  }

  const TEMPLATE_LABELS = {
    clean_white: 'Clean White',
    soft_grey: 'Soft Grey',
    minimal_border: 'Minimal Border',
    rounded_card: 'Rounded Card',
    glass_overlay: 'Glass Overlay'
  };

  function setStudioTemplate(tpl) {
    studioTemplate = tpl;
    document.getElementById('studio-active-template-label').textContent = TEMPLATE_LABELS[tpl] || tpl;
    Object.keys(TEMPLATE_LABELS).forEach(k => {
      const btn = document.getElementById('tpl-' + k);
      if (!btn) return;
      if (k === tpl) {
        btn.className = 'p-3 rounded-2xl border-2 border-primary bg-primary-fixed/15 text-left transition-all';
      } else {
        btn.className = 'p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all';
      }
    });
    refreshStudioCanvas();
    saveGlobalFramePreset(true);
  }

  async function saveGlobalFramePreset(silent = false) {
    const captionOn = document.getElementById('studio-caption-toggle')?.checked ?? true;
    const model = document.getElementById('studio-model-input')?.value || '';
    const price = document.getElementById('studio-price-input')?.value || '';
    const specs = document.getElementById('studio-specs-input')?.value || '';
    const fb = document.getElementById('studio-save-feedback');

    const res = await fetch('/api/frame-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        ratio: studioRatio,
        fit_mode: studioFitMode,
        template_style: studioTemplate,
        offset_x: studioOffsetX,
        offset_y: studioOffsetY,
        caption_enabled: captionOn,
        car_model: model,
        car_price: price,
        car_specs: specs
      })
    });
    if (res.ok) {
      const data = await res.json();
      syncUiWithFrameConfig(data.frame_config);
      if (!silent && fb) {
        fb.textContent = `Default Frame Preset saved (${TEMPLATE_LABELS[studioTemplate] || studioTemplate} • ${studioRatio}) and applied!`;
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 3500);
      }
      await fetchState();
    }
  }

  async function uploadCustomPlateOverlay(fileList) {
    if (!fileList || !fileList.length) return;
    const file = fileList[0];
    const fd = new FormData();
    fd.append('file', file);
    const fb = document.getElementById('overlay-upload-feedback');

    const res = await fetch('/api/plate-overlay', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin'
    });
    if (res.ok) {
      const prev = document.getElementById('plate-overlay-preview-img');
      if (prev) prev.src = '/media/plate-overlay?t=' + Date.now();
      if (fb) {
        fb.textContent = `Plate cover updated (${file.name}) and applied to all vehicles!`;
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 4000);
      }
      refreshStudioCanvas();
      await fetchState();
    }
  }

  async function resetCustomPlateOverlay() {
    const fb = document.getElementById('overlay-upload-feedback');
    const res = await fetch('/api/plate-overlay', {
      method: 'DELETE',
      credentials: 'same-origin'
    });
    if (res.ok) {
      const prev = document.getElementById('plate-overlay-preview-img');
      if (prev) prev.src = '/media/plate-overlay?t=' + Date.now();
      if (fb) {
        fb.textContent = 'Reset to default Forest Wheel plate cover.';
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 3500);
      }
      refreshStudioCanvas();
      await fetchState();
    }
  }

  function buildStudioRenderUrl(download = 0) {
    const captionOn = document.getElementById('studio-caption-toggle')?.checked ? 1 : 0;
    const model = document.getElementById('studio-model-input')?.value || '';
    const price = document.getElementById('studio-price-input')?.value || '';
    const specs = document.getElementById('studio-specs-input')?.value || '';

    const params = new URLSearchParams({
      ratio: studioRatio,
      fit_mode: studioFitMode,
      template_style: studioTemplate,
      offset_x: studioOffsetX.toFixed(2),
      offset_y: studioOffsetY.toFixed(2),
      caption: String(captionOn),
      car_model: model,
      car_price: price,
      car_specs: specs,
      download: String(download)
    });
    if (studioCarId) params.set('car_id', studioCarId);
    if (studioFilename) params.set('filename', studioFilename);
    return `/api/frame-render?${params.toString()}`;
  }

  function refreshStudioCanvas() {
    const img = document.getElementById('studio-preview-img');
    if (!img) return;
    img.src = buildStudioRenderUrl(0);
  }

  function debouncedRefreshStudio() {
    if (studioDebounceTimer) clearTimeout(studioDebounceTimer);
    studioDebounceTimer = setTimeout(refreshStudioCanvas, 280);
  }

  // Drag / pinch to reposition when in "Fill frame" mode
  function startCanvasPan(ev) {
    if (studioFitMode !== 'fill') return;
    isPanning = true;
    const pt = ev.touches ? ev.touches[0] : ev;
    panStartX = pt.clientX;
    panStartY = pt.clientY;
  }

  function moveCanvasPan(ev) {
    if (!isPanning || studioFitMode !== 'fill') return;
    const pt = ev.touches ? ev.touches[0] : ev;
    const dx = (panStartX - pt.clientX) / 260;
    const dy = (panStartY - pt.clientY) / 260;
    panStartX = pt.clientX;
    panStartY = pt.clientY;
    studioOffsetX = Math.max(0.0, Math.min(1.0, studioOffsetX + dx));
    studioOffsetY = Math.max(0.0, Math.min(1.0, studioOffsetY + dy));
    debouncedRefreshStudio();
  }

  function endCanvasPan() {
    isPanning = false;
  }

  async function saveStudioFrameToGallery() {
    const captionOn = document.getElementById('studio-caption-toggle')?.checked ?? true;
    const model = document.getElementById('studio-model-input')?.value || '';
    const price = document.getElementById('studio-price-input')?.value || '';
    const specs = document.getElementById('studio-specs-input')?.value || '';
    const fb = document.getElementById('studio-save-feedback');

    const res = await fetch('/api/frame-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        car_id: studioCarId || 'SXX-1234-A',
        filename: studioFilename || 'showroom.jpg',
        ratio: studioRatio,
        fit_mode: studioFitMode,
        template_style: studioTemplate,
        offset_x: studioOffsetX,
        offset_y: studioOffsetY,
        caption: captionOn,
        car_model: model,
        car_price: price,
        car_specs: specs
      })
    });
    if (res.ok) {
      const data = await res.json();
      if (fb) {
        fb.textContent = `Saved ${data.saved_filename} to ${data.car_id} in Gallery!`;
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 3500);
      }
      await fetchState();
    }
  }

  function exportStudioFrame() {
    window.location.href = buildStudioRenderUrl(1);
  }

  // Initialize on page load
  window.addEventListener('DOMContentLoaded', () => {
    renderUploadQueue();
    fetchState();
  });
</script>
</body>
</html>
"""
