"""HTML template for the Stitch-aligned Forest Wheel Plate Removal System UI."""

from __future__ import annotations

STITCH_UI_HTML = r"""<!DOCTYPE html>
<html class="dark" lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>Forest Wheel — Plate Removal &amp; Template Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap" rel="stylesheet" />
  <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            "on-error": "#690005",
            "slate-border": "#2B352E",
            "primary": "#a5d0b9",
            "on-background": "#e0e3df",
            "secondary": "#95d4b3",
            "background": "#101412",
            "on-primary": "#0e3727",
            "surface-container-low": "#181c1a",
            "primary-container": "#1b4332",
            "surface": "#101412",
            "on-tertiary": "#4c2700",
            "on-surface": "#e0e3df",
            "tertiary-container": "#5c3100",
            "slate-surface": "#181D1A",
            "status-processing": "#F68E13",
            "on-tertiary-container": "#f48c10",
            "primary-fixed": "#c1ecd4",
            "surface-container-highest": "#323633",
            "surface-container": "#1c201e",
            "surface-bright": "#363a38",
            "error-container": "#93000a",
            "surface-container-high": "#272b29",
            "surface-dim": "#101412",
            "status-error": "#D9383A",
            "slate-elevated": "#202622",
            "tertiary": "#ffb778",
            "error": "#ffb4ab",
            "outline-variant": "#414844",
            "inverse-primary": "#3f6653",
            "status-synced": "#40916C",
            "on-surface-variant": "#c1c8c2",
            "surface-container-lowest": "#0b0f0d",
            "lens-grid": "#52B788",
            "outline": "#8b938d",
            "secondary-container": "#12533a"
          },
          fontFamily: {
            headline: ["Outfit", "sans-serif"],
            body: ["Inter", "sans-serif"],
            mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"]
          }
        }
      }
    };
  </script>
  <style>
    html, body { margin: 0; padding: 0; background: #101412; color: #e0e3df; font-family: 'Inter', sans-serif; }
    .font-headline { font-family: 'Outfit', sans-serif; }
    .tabular-nums { font-variant-numeric: tabular-nums; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #101412; }
    ::-webkit-scrollbar-thumb { background: #2B352E; border-radius: 3px; }
    .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 20; vertical-align: middle; }
  </style>
</head>
<body class="bg-background text-on-surface antialiased min-h-screen flex flex-col lg:flex-row">

  <!-- Left Workbench Sidebar (Stitch ForestWheel Plate Removal System) -->
  <aside class="lg:fixed lg:left-0 lg:top-0 lg:h-full lg:w-72 bg-surface-container-low border-b lg:border-b-0 lg:border-r border-slate-border z-50 flex flex-col justify-between shrink-0">
    <div class="flex flex-col">
      <!-- Brand Header -->
      <div class="h-16 px-5 flex items-center justify-between border-b border-slate-border">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded bg-primary-container border border-lens-grid/40 flex items-center justify-center text-primary font-headline font-bold text-lg shadow-sm">
            FW
          </div>
          <div class="flex flex-col min-w-0">
            <span class="font-headline text-lg font-semibold text-on-surface truncate tracking-tight">Forest Wheel</span>
            <span class="text-[10px] font-semibold text-primary uppercase tracking-widest">Plate Removal System</span>
          </div>
        </div>
        <span class="lg:hidden px-2 py-0.5 rounded bg-primary-container/60 border border-primary/30 text-[10px] font-mono text-primary">v2.5</span>
      </div>

      <!-- Watch Status Pill -->
      <div class="p-4">
        <div class="p-2.5 rounded-lg bg-surface-container-high border border-slate-border flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-status-synced animate-pulse"></span>
            <span class="text-[10px] font-semibold text-on-surface-variant uppercase tracking-wider">Watch Status</span>
          </div>
          <span class="px-2 py-0.5 rounded bg-primary-container/60 border border-primary/30 text-[10px] font-semibold text-primary">YOLOv8 CPU Ready</span>
        </div>

        <div class="px-1 mb-1.5">
          <span class="text-[10px] font-semibold text-outline uppercase tracking-wider">Workspaces</span>
        </div>

        <!-- 4 Stitch Workspaces Navigation -->
        <nav class="grid grid-cols-2 lg:flex lg:flex-col gap-1.5" id="sidebar-nav">
          <button type="button" onclick="switchTab('upload')" id="nav-upload"
            class="nav-btn flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors bg-primary-container text-primary font-semibold border-l-2 border-primary">
            <span class="material-symbols-outlined text-xl">cloud_upload</span>
            <div class="flex flex-col min-w-0">
              <span class="text-xs font-semibold truncate">Upload &amp; Watcher Hub</span>
              <span class="text-[10px] text-outline truncate">Multi-upload &amp; 1:1 / 16:9 / 9:16</span>
            </div>
          </button>

          <button type="button" onclick="switchTab('galleries')" id="nav-galleries"
            class="nav-btn flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-on-surface-variant hover:bg-slate-elevated hover:text-on-surface transition-colors">
            <span class="material-symbols-outlined text-xl">directions_car</span>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-semibold truncate">Vehicle Galleries</span>
                <span id="badge-galleries-count" class="px-1.5 py-0.2 rounded-full bg-surface-container-highest text-[10px] font-mono text-primary">0</span>
              </div>
              <span class="text-[10px] text-outline truncate">/output/&lt;car-id&gt; &amp; crop ratios</span>
            </div>
          </button>

          <button type="button" onclick="switchTab('review')" id="nav-review"
            class="nav-btn flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-on-surface-variant hover:bg-slate-elevated hover:text-on-surface transition-colors">
            <span class="material-symbols-outlined text-xl">find_in_page</span>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-semibold truncate">Plate Review UI</span>
                <span id="badge-review-count" class="px-1.5 py-0.2 rounded-full bg-status-processing/20 text-status-processing text-[10px] font-mono font-bold">0</span>
              </div>
              <span class="text-[10px] text-outline truncate">Split inspector &amp; 4-pin warp</span>
            </div>
          </button>

          <button type="button" onclick="switchTab('studio')" id="nav-studio"
            class="nav-btn flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-on-surface-variant hover:bg-slate-elevated hover:text-on-surface transition-colors">
            <span class="material-symbols-outlined text-xl">aspect_ratio</span>
            <div class="flex flex-col min-w-0">
              <span class="text-xs font-semibold truncate">Template Studio</span>
              <span class="text-[10px] text-outline truncate">1:1, 16:9 &amp; 9:16 crop presets</span>
            </div>
          </button>
        </nav>
      </div>
    </div>

    <!-- Bottom Pipeline IO Health -->
    <div class="hidden lg:block p-4 border-t border-slate-border">
      <div class="bg-surface-container rounded-lg p-3 border border-slate-border flex flex-col gap-1.5">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-semibold text-outline uppercase">Pipeline IO</span>
          <span class="text-[10px] font-bold text-status-synced">FAIL-SAFE ACTIVE</span>
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="text-on-surface-variant">Active Ratio</span>
          <span id="sidebar-active-ratio" class="font-mono text-primary font-semibold">16:9 (1920×1080)</span>
        </div>
        <div class="w-full bg-surface-container-highest rounded-full h-1 mt-0.5">
          <div class="bg-lens-grid h-1 rounded-full w-4/5"></div>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content Shell -->
  <div class="lg:pl-72 flex-1 flex flex-col min-h-screen">
    <!-- Top Telemetry Bar -->
    <header class="sticky top-0 h-16 bg-surface-container-low/95 backdrop-blur-md border-b border-slate-border z-40 px-4 lg:px-8 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2.5 overflow-x-auto py-1">
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-surface border border-slate-border shrink-0">
          <span class="w-2 h-2 rounded-full bg-status-synced"></span>
          <span class="text-[10px] font-semibold text-outline uppercase">YOLOv8 Plate Model:</span>
          <span class="text-[11px] font-mono text-on-surface font-semibold">plate_yolov8n.pt</span>
        </div>
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-surface border border-slate-border shrink-0">
          <span class="w-2 h-2 rounded-full bg-primary"></span>
          <span class="text-[10px] font-semibold text-outline uppercase">Crop Ratios:</span>
          <span class="text-[11px] font-mono text-primary font-semibold">1:1 • 16:9 • 9:16</span>
        </div>
        <div class="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-surface border border-slate-border shrink-0">
          <span class="w-2 h-2 rounded-full bg-status-synced"></span>
          <span class="text-[10px] font-semibold text-outline uppercase">Rule #2:</span>
          <span class="text-[11px] text-on-surface font-semibold">No Plate, No Publish</span>
        </div>
      </div>

      <!-- Global Ratio Quick-Select & Refresh -->
      <div class="flex items-center gap-2 shrink-0">
        <div class="flex items-center bg-surface-container-lowest p-0.5 rounded-lg border border-slate-border">
          <button type="button" onclick="setGlobalRatio('1:1')" data-ratio-btn="1:1"
            class="ratio-pill px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all text-on-surface-variant hover:text-on-surface">
            1:1
          </button>
          <button type="button" onclick="setGlobalRatio('16:9')" data-ratio-btn="16:9"
            class="ratio-pill px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all bg-primary-container text-primary">
            16:9
          </button>
          <button type="button" onclick="setGlobalRatio('9:16')" data-ratio-btn="9:16"
            class="ratio-pill px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all text-on-surface-variant hover:text-on-surface">
            9:16
          </button>
        </div>
        <button type="button" onclick="refreshAllState()" title="Refresh State"
          class="p-2 rounded-lg bg-surface-container-high border border-slate-border text-on-surface-variant hover:text-primary transition-colors">
          <span class="material-symbols-outlined text-base">refresh</span>
        </button>
      </div>
    </header>

    <!-- ===================================================================== -->
    <!-- WORKSPACE 1: UPLOAD & WATCHER HUB                                     -->
    <!-- ===================================================================== -->
    <main id="view-upload" class="workspace-view flex-1 p-4 lg:p-8 max-w-[1680px] w-full mx-auto space-y-6">
      <!-- Top Telemetry Banner -->
      <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        <!-- Multi-File Upload & Ratio Ingestion Card -->
        <div class="xl:col-span-7 bg-surface-container rounded-xl p-6 border border-slate-border flex flex-col justify-between relative overflow-hidden">
          <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between flex-wrap gap-2">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-primary-container border border-lens-grid/30 flex items-center justify-center text-primary">
                  <span class="material-symbols-outlined text-2xl">cloud_upload</span>
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <h2 class="font-headline text-xl font-semibold text-on-surface">Direct Multi-Photo Batch Ingestion</h2>
                    <span class="px-2 py-0.5 rounded bg-lens-grid/15 text-lens-grid text-[10px] font-bold uppercase tracking-wider">Instant YOLO</span>
                  </div>
                  <p class="text-xs text-on-surface-variant">Upload multiple vehicle photos to automatically cover license plates and generate 1:1, 16:9, or 9:16 cropped templates.</p>
                </div>
              </div>
            </div>

            <!-- Car ID Input + Template Ratio Selector -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-4 pt-1">
              <div class="md:col-span-6 flex flex-col gap-1">
                <label class="text-[10px] font-semibold text-outline uppercase tracking-wider" for="upload-car-id">Assigned Car ID / Inventory Slug</label>
                <div class="relative">
                  <span class="material-symbols-outlined absolute left-3 top-2.5 text-base text-outline">directions_car</span>
                  <input id="upload-car-id" type="text" value="FW-2026-911GT3" placeholder="e.g. FW-2026-911GT3"
                    class="w-full bg-surface-container-lowest border border-slate-border rounded-lg pl-9 pr-3 py-2 text-sm text-on-surface font-mono focus:outline-none focus:border-lens-grid" />
                </div>
                <div class="flex items-center gap-1.5 mt-1">
                  <span class="text-[10px] text-outline">Presets:</span>
                  <button type="button" onclick="document.getElementById('upload-car-id').value='FW-2026-911GT3'" class="px-2 py-0.5 rounded bg-surface-container-high hover:bg-slate-elevated text-[10px] font-mono text-secondary">911GT3</button>
                  <button type="button" onclick="document.getElementById('upload-car-id').value='FW-2025-RS6AV'" class="px-2 py-0.5 rounded bg-surface-container-high hover:bg-slate-elevated text-[10px] font-mono text-secondary">RS6AV</button>
                  <button type="button" onclick="document.getElementById('upload-car-id').value='FW-2024-G63AMG'" class="px-2 py-0.5 rounded bg-surface-container-high hover:bg-slate-elevated text-[10px] font-mono text-secondary">G63AMG</button>
                </div>
              </div>

              <div class="md:col-span-6 flex flex-col gap-1">
                <label class="text-[10px] font-semibold text-outline uppercase tracking-wider">Target Template Crop Ratio</label>
                <div class="grid grid-cols-3 gap-2">
                  <button type="button" onclick="setGlobalRatio('1:1')" data-upload-ratio="1:1"
                    class="upload-ratio-btn flex flex-col items-center justify-center py-2 px-2 rounded-lg border border-slate-border bg-surface-container-lowest hover:bg-surface-container-high transition-all">
                    <span class="material-symbols-outlined text-base text-primary">crop_square</span>
                    <span class="text-xs font-mono font-bold mt-0.5">1:1</span>
                    <span class="text-[10px] text-outline">1080×1080</span>
                  </button>
                  <button type="button" onclick="setGlobalRatio('16:9')" data-upload-ratio="16:9"
                    class="upload-ratio-btn flex flex-col items-center justify-center py-2 px-2 rounded-lg border border-lens-grid bg-primary-container/60 text-primary transition-all">
                    <span class="material-symbols-outlined text-base text-primary">crop_16_9</span>
                    <span class="text-xs font-mono font-bold mt-0.5">16:9</span>
                    <span class="text-[10px] text-primary/80">1920×1080</span>
                  </button>
                  <button type="button" onclick="setGlobalRatio('9:16')" data-upload-ratio="9:16"
                    class="upload-ratio-btn flex flex-col items-center justify-center py-2 px-2 rounded-lg border border-slate-border bg-surface-container-lowest hover:bg-surface-container-high transition-all">
                    <span class="material-symbols-outlined text-base text-primary">crop_portrait</span>
                    <span class="text-xs font-mono font-bold mt-0.5">9:16</span>
                    <span class="text-[10px] text-outline">1080×1920</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Interactive Multi-File Dropzone -->
            <input id="file-input" type="file" multiple accept=".jpg,.jpeg,.png,.heic" class="hidden" onchange="handleFilesSelected(this.files)" />
            <div id="dropzone"
              onclick="document.getElementById('file-input').click()"
              ondragover="event.preventDefault(); this.classList.add('border-lens-grid', 'bg-surface-container-high');"
              ondragleave="this.classList.remove('border-lens-grid', 'bg-surface-container-high');"
              ondrop="event.preventDefault(); this.classList.remove('border-lens-grid', 'bg-surface-container-high'); handleFilesSelected(event.dataTransfer.files);"
              class="bg-surface-container-lowest border-2 border-dashed border-slate-border hover:border-lens-grid rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all min-h-[200px] group">
              <div class="w-14 h-14 rounded-full bg-surface-container flex items-center justify-center text-lens-grid group-hover:scale-105 transition-transform mb-2">
                <span class="material-symbols-outlined text-3xl">add_photo_alternate</span>
              </div>
              <span class="font-headline text-base font-semibold text-on-surface">
                Drop multiple vehicle photos here or <span class="text-primary underline">browse files</span>
              </span>
              <p class="text-xs text-on-surface-variant max-w-md mt-1">
                Supports batch upload of JPG, PNG, and HEIC photos. Every photo is scanned by YOLOv8, plate-masked with perspective warp, and cropped into your selected template ratio.
              </p>
              <div id="selected-files-pill" class="hidden mt-3 px-3 py-1 rounded-full bg-primary-container text-primary text-xs font-mono font-semibold"></div>
            </div>

            <!-- Upload Progress & Action Button -->
            <div id="upload-progress-wrap" class="hidden flex-col gap-1.5 bg-surface-container-low p-3 rounded-lg border border-slate-border">
              <div class="flex items-center justify-between text-xs">
                <span id="upload-status-text" class="text-status-processing font-medium flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                  Running YOLOv8 Plate Detection &amp; Perspective Composite...
                </span>
                <span id="upload-pct-text" class="font-mono text-on-surface font-semibold">...</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-2 overflow-hidden">
                <div id="upload-progress-bar" class="bg-status-processing h-2 rounded-full w-1/2 animate-pulse"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Automated Synthesis Flags & Google Drive Sync Card -->
        <div class="xl:col-span-5 bg-surface-container rounded-xl p-6 border border-slate-border flex flex-col justify-between gap-4">
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">tune</span>
                <h3 class="font-headline text-lg font-semibold text-on-surface">Automated Synthesis Flags</h3>
              </div>
              <span class="text-[10px] font-mono text-status-synced font-semibold uppercase">CONFIG ACTIVE</span>
            </div>

            <div class="flex flex-col gap-2">
              <label class="flex items-start gap-3 p-2.5 rounded-lg bg-surface-container-low border border-slate-border/60 cursor-pointer">
                <input type="checkbox" checked disabled class="mt-1 accent-primary w-4 h-4 rounded" />
                <div class="flex flex-col">
                  <span class="text-xs font-semibold text-on-surface">Auto-run Plate Detection (YOLOv8 CPU)</span>
                  <span class="text-[11px] text-outline">Downscales 4K frames for inference and maps coordinates back to original resolution.</span>
                </div>
              </label>

              <label class="flex items-start gap-3 p-2.5 rounded-lg bg-surface-container-low border border-slate-border/60 cursor-pointer">
                <input type="checkbox" id="flag-perspective" checked class="mt-1 accent-primary w-4 h-4 rounded" />
                <div class="flex flex-col">
                  <span class="text-xs font-semibold text-on-surface">4-Corner Perspective Homography Warp</span>
                  <span class="text-[11px] text-outline">Detects dominant plate quadrilateral via Canny + contours and warps Forest Wheel overlay.</span>
                </div>
              </label>

              <label class="flex items-start gap-3 p-2.5 rounded-lg bg-surface-container-low border border-slate-border/60 cursor-pointer">
                <input type="checkbox" checked disabled class="mt-1 accent-status-processing w-4 h-4 rounded" />
                <div class="flex flex-col">
                  <div class="flex items-center gap-1.5">
                    <span class="text-xs font-semibold text-on-surface">Fail-Safe Quarantine (&lt;40% Conf / No Plate)</span>
                    <span class="px-1.5 py-0.2 rounded bg-tertiary-container/40 text-tertiary text-[10px] font-semibold">Hard Rule #2</span>
                  </div>
                  <span class="text-[11px] text-outline">Routes uncertain or interior shots to Plate Review UI so no uncovered plate is ever published.</span>
                </div>
              </label>
            </div>
          </div>

          <!-- Quick Demo Sample Batch Trigger -->
          <div class="pt-3 border-t border-slate-border flex items-center justify-between flex-wrap gap-2">
            <div class="text-xs text-on-surface-variant">
              Want to test with sample photos?
            </div>
            <button type="button" onclick="runDemoSampleBatch()"
              class="px-3.5 py-2 rounded-lg bg-surface-container-high hover:bg-slate-elevated border border-slate-border text-xs font-semibold text-primary flex items-center gap-1.5 transition-colors">
              <span class="material-symbols-outlined text-base">play_arrow</span>
              Process Test Photos Batch
            </button>
          </div>
        </div>
      </div>

      <!-- Real-Time Ingestion & Processing Queue Table -->
      <div class="bg-surface-container rounded-xl p-6 border border-slate-border flex flex-col gap-4">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center gap-2.5">
            <span class="material-symbols-outlined text-secondary text-2xl">precision_manufacturing</span>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-headline text-lg font-semibold text-on-surface">Processed &amp; Queued Vehicle Batches</h3>
                <span id="queue-batch-count" class="px-2 py-0.5 rounded-full bg-surface-container-high text-primary font-mono text-[10px] font-semibold">0 BATCHES</span>
              </div>
              <p class="text-xs text-on-surface-variant">Click any vehicle batch to inspect finished 1:1 / 16:9 / 9:16 exports or review flagged plates.</p>
            </div>
          </div>
        </div>

        <div id="batches-list" class="flex flex-col gap-2.5"></div>
      </div>
    </main>

    <!-- ===================================================================== -->
    <!-- WORKSPACE 2: VEHICLE GALLERIES & MULTI-RATIO EXPORT                   -->
    <!-- ===================================================================== -->
    <main id="view-galleries" class="workspace-view hidden flex-1 p-4 lg:p-8 max-w-[1680px] w-full mx-auto space-y-6">
      <div class="bg-surface-container-low rounded-xl p-6 border border-slate-border flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[10px] font-semibold text-primary uppercase tracking-widest">Syndication &amp; Crop Hub</span>
            <span class="text-outline font-mono text-xs">/output/&lt;car-id&gt;</span>
          </div>
          <h1 class="font-headline text-2xl font-semibold text-on-surface">Vehicle Galleries &amp; Aspect-Ratio Crops</h1>
          <p class="text-xs text-on-surface-variant mt-0.5">Preview and export plate-covered photos in Square (1:1), Widescreen (16:9), or Vertical Story (9:16) templates.</p>
        </div>

        <!-- Ratio Switcher in Gallery Header -->
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs text-outline mr-1">Preview &amp; Export Ratio:</span>
          <button type="button" onclick="setGlobalRatio('1:1')" data-ratio-btn="1:1"
            class="ratio-pill px-3 py-2 rounded-lg text-xs font-mono font-semibold border border-slate-border bg-surface-container text-on-surface-variant">
            1:1 Square (1080×1080)
          </button>
          <button type="button" onclick="setGlobalRatio('16:9')" data-ratio-btn="16:9"
            class="ratio-pill px-3 py-2 rounded-lg text-xs font-mono font-semibold border border-lens-grid bg-primary-container text-primary">
            16:9 Wide (1920×1080)
          </button>
          <button type="button" onclick="setGlobalRatio('9:16')" data-ratio-btn="9:16"
            class="ratio-pill px-3 py-2 rounded-lg text-xs font-mono font-semibold border border-slate-border bg-surface-container text-on-surface-variant">
            9:16 Story (1080×1920)
          </button>
        </div>
      </div>

      <div id="galleries-container" class="space-y-6"></div>
    </main>

    <!-- ===================================================================== -->
    <!-- WORKSPACE 3: PLATE REVIEW UI (SPLIT INSPECTOR & 4-PIN WARP)           -->
    <!-- ===================================================================== -->
    <main id="view-review" class="workspace-view hidden flex-1 flex flex-col max-w-[1680px] w-full mx-auto">
      <!-- Top Review Subbar -->
      <div class="w-full bg-surface-container-low border-b border-slate-border px-4 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2 bg-surface-container px-3 py-1.5 rounded-lg border border-slate-border">
            <span class="material-symbols-outlined text-status-processing">fact_check</span>
            <div class="flex flex-col">
              <span class="text-[10px] text-outline uppercase">Active Review Item</span>
              <span id="review-active-title" class="font-headline text-sm font-semibold text-on-surface">Select an item below</span>
            </div>
          </div>
          <span id="review-reason-pill" class="px-2.5 py-1 rounded-full bg-status-processing/15 border border-status-processing/40 text-status-processing text-xs font-mono font-semibold">
            No item selected
          </span>
        </div>

        <div class="flex items-center gap-2 text-xs text-outline">
          <span class="hidden sm:inline">Hotkeys:</span>
          <kbd class="px-1.5 py-0.5 rounded bg-surface-container-highest text-on-surface font-mono">[A]</kbd> Approve
          <kbd class="px-1.5 py-0.5 rounded bg-surface-container-highest text-on-surface font-mono">[R]</kbd> Reject
        </div>
      </div>

      <!-- Main Split Studio Stage & Parameter Sidebar -->
      <div class="p-4 lg:p-8 grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
        <!-- Left/Center: Split Before/After Comparison + 4 Draggable Pins -->
        <div class="lg:col-span-8 xl:col-span-9 flex flex-col gap-4">
          <div id="inspector-stage" class="relative w-full aspect-[16/10] bg-surface-container-lowest rounded-xl border border-slate-border overflow-hidden select-none flex items-center justify-center">
            <div id="review-empty-msg" class="text-center p-8">
              <span class="material-symbols-outlined text-4xl text-status-synced mb-2">verified</span>
              <h3 class="font-headline text-lg font-semibold text-on-surface">Review Queue is Clear</h3>
              <p class="text-xs text-on-surface-variant mt-1">All uploaded photos had high-confidence license plate detections or have been reviewed.</p>
            </div>

            <!-- Before Layer (Raw Image) -->
            <img id="review-before-img" class="hidden absolute inset-0 w-full h-full object-contain pointer-events-none" alt="Before Raw" />

            <!-- After Layer (Clipped by Split Slider) -->
            <div id="review-after-clip" class="hidden absolute inset-0 w-full h-full overflow-hidden pointer-events-none" style="clip-path: polygon(50% 0, 100% 0, 100% 100%, 50% 100%);">
              <img id="review-after-img" class="w-full h-full object-contain" alt="After Processed" />
            </div>

            <!-- Badges -->
            <div id="review-badges" class="hidden">
              <div class="absolute top-3 left-3 z-20 flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-highest/90 text-on-surface text-xs font-semibold">
                <span class="w-2 h-2 rounded-full bg-status-error"></span>
                BEFORE (Raw in review/)
              </div>
              <div class="absolute top-3 right-3 z-20 flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-container/90 text-primary text-xs font-semibold">
                <span class="material-symbols-outlined text-sm">auto_fix_high</span>
                AFTER (<span id="review-stage-ratio-label">16:9</span> Template Preview)
              </div>
            </div>

            <!-- Interactive 4-Corner Overlay Calibration Pins (Optional Manual Override) -->
            <svg id="pin-svg-layer" class="hidden absolute inset-0 w-full h-full z-30 pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polygon id="pin-polygon" points="35,60 65,60 65,75 35,75" fill="rgba(82, 183, 136, 0.14)" stroke="#52B788" stroke-width="0.6" stroke-dasharray="1.5 1" />
            </svg>
            <div id="pins-wrapper" class="hidden absolute inset-0 z-30 pointer-events-none">
              <div data-pin="0" class="pin-handle pointer-events-auto absolute w-6 h-6 -ml-3 -mt-3 rounded-full bg-surface-container-lowest border-2 border-lens-grid flex items-center justify-center cursor-grab shadow-lg" style="left:35%;top:60%;">
                <span class="text-[9px] font-mono text-primary font-bold">P1</span>
              </div>
              <div data-pin="1" class="pin-handle pointer-events-auto absolute w-6 h-6 -ml-3 -mt-3 rounded-full bg-surface-container-lowest border-2 border-lens-grid flex items-center justify-center cursor-grab shadow-lg" style="left:65%;top:60%;">
                <span class="text-[9px] font-mono text-primary font-bold">P2</span>
              </div>
              <div data-pin="2" class="pin-handle pointer-events-auto absolute w-6 h-6 -ml-3 -mt-3 rounded-full bg-surface-container-lowest border-2 border-lens-grid flex items-center justify-center cursor-grab shadow-lg" style="left:65%;top:75%;">
                <span class="text-[9px] font-mono text-primary font-bold">P3</span>
              </div>
              <div data-pin="3" class="pin-handle pointer-events-auto absolute w-6 h-6 -ml-3 -mt-3 rounded-full bg-surface-container-lowest border-2 border-lens-grid flex items-center justify-center cursor-grab shadow-lg" style="left:35%;top:75%;">
                <span class="text-[9px] font-mono text-primary font-bold">P4</span>
              </div>
            </div>

            <!-- Split Slider Bar -->
            <div id="split-slider-handle" class="hidden absolute top-0 bottom-0 z-40 cursor-ew-resize flex items-center justify-center" style="left: 50%; width: 28px; margin-left: -14px;">
              <div class="w-0.5 h-full bg-lens-grid shadow-[0_0_10px_rgba(82,183,136,0.9)]"></div>
              <div class="w-9 h-9 rounded-full bg-surface-container-high border border-lens-grid text-lens-grid flex items-center justify-center shadow-xl absolute">
                <span class="material-symbols-outlined text-base">compare_arrows</span>
              </div>
            </div>
          </div>

          <!-- Review Queue Reel -->
          <div class="bg-surface-container-low rounded-xl p-3 border border-slate-border flex items-center gap-3 overflow-x-auto">
            <span class="text-[10px] font-semibold text-outline uppercase tracking-wider shrink-0 pl-1">Review Reel:</span>
            <div id="review-reel-list" class="flex items-center gap-2"></div>
          </div>
        </div>

        <!-- Right Inspector: Manual Plate Box & Ratio Calibration -->
        <div class="lg:col-span-4 xl:col-span-3 flex flex-col justify-between gap-4">
          <div class="bg-surface-container-low rounded-xl p-5 border border-slate-border flex flex-col gap-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">tune</span>
                <h3 class="font-headline text-base font-semibold text-on-surface">Review &amp; Warp Controls</h3>
              </div>
              <button type="button" onclick="toggleManualPins()" id="btn-toggle-pins"
                class="px-2 py-1 rounded bg-surface-container-high text-xs font-mono text-primary hover:bg-slate-elevated">
                Show 4-Pin Overlay
              </button>
            </div>

            <!-- Coordinate Readout -->
            <div class="grid grid-cols-2 gap-2 bg-surface-container p-2.5 rounded-lg font-mono text-xs border border-slate-border">
              <div class="p-1.5 rounded bg-surface-container-low">
                <div class="text-[10px] text-outline">P1 (TL)</div>
                <div id="coord-p1" class="text-on-surface">35% , 60%</div>
              </div>
              <div class="p-1.5 rounded bg-surface-container-low">
                <div class="text-[10px] text-outline">P2 (TR)</div>
                <div id="coord-p2" class="text-on-surface">65% , 60%</div>
              </div>
              <div class="p-1.5 rounded bg-surface-container-low">
                <div class="text-[10px] text-outline">P4 (BL)</div>
                <div id="coord-p4" class="text-on-surface">35% , 75%</div>
              </div>
              <div class="p-1.5 rounded bg-surface-container-low">
                <div class="text-[10px] text-outline">P3 (BR)</div>
                <div id="coord-p3" class="text-on-surface">65% , 75%</div>
              </div>
            </div>

            <!-- Split Slider Range Input (Accessible on Mobile/iPad) -->
            <div class="flex flex-col gap-1">
              <div class="flex justify-between text-xs">
                <span class="text-on-surface-variant">Before / After Split Position</span>
                <span id="split-pct-label" class="font-mono text-primary">50%</span>
              </div>
              <input id="split-range-input" type="range" min="0" max="100" value="50" oninput="setSplitPercent(this.value)"
                class="w-full accent-primary h-1.5 bg-surface-container-high rounded-lg cursor-pointer" />
            </div>

            <!-- Output Ratio Selection for Approval -->
            <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-border">
              <span class="text-[10px] font-semibold text-outline uppercase tracking-wider">Export Template Ratio on Approve</span>
              <div class="grid grid-cols-3 gap-1.5">
                <button type="button" onclick="setGlobalRatio('1:1')" data-ratio-btn="1:1" class="ratio-pill py-1.5 rounded bg-surface-container text-xs font-mono">1:1</button>
                <button type="button" onclick="setGlobalRatio('16:9')" data-ratio-btn="16:9" class="ratio-pill py-1.5 rounded bg-primary-container text-primary text-xs font-mono font-bold">16:9</button>
                <button type="button" onclick="setGlobalRatio('9:16')" data-ratio-btn="9:16" class="ratio-pill py-1.5 rounded bg-surface-container text-xs font-mono">9:16</button>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex flex-col gap-2.5 pt-2">
              <button type="button" onclick="submitReviewDecision('approve')"
                class="w-full h-12 rounded-xl bg-primary-container hover:bg-secondary-container border border-lens-grid/50 text-primary hover:text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg transition-all">
                <span class="material-symbols-outlined">check_circle</span>
                Approve &amp; Move to /output
              </button>
              <button type="button" onclick="submitReviewDecision('reject')"
                class="w-full h-11 rounded-xl bg-surface-container hover:bg-error-container/30 border border-slate-border text-on-surface hover:text-error font-semibold text-xs flex items-center justify-center gap-2 transition-all">
                <span class="material-symbols-outlined text-base">close</span>
                Reject (Keep in /review)
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- ===================================================================== -->
    <!-- WORKSPACE 4: TEMPLATE STUDIO (1:1, 16:9, 9:16 CROP COMPOSITOR)        -->
    <!-- ===================================================================== -->
    <main id="view-studio" class="workspace-view hidden flex-1 p-4 lg:p-8 max-w-[1680px] w-full mx-auto space-y-6">
      <div class="bg-surface-container rounded-xl p-5 border border-slate-border flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center text-primary">
            <span class="material-symbols-outlined text-2xl">aspect_ratio</span>
          </div>
          <div>
            <h2 class="font-headline text-xl font-semibold text-on-surface">Template Studio &amp; Multi-Ratio Cropper</h2>
            <p class="text-xs text-on-surface-variant font-mono">config/template.yaml • Live Pillow Aspect-Ratio Preview</p>
          </div>
        </div>

        <!-- Ratio Tabs -->
        <div class="flex p-1 bg-surface-container-lowest rounded-lg border border-slate-border">
          <button type="button" onclick="setGlobalRatio('1:1')" data-ratio-btn="1:1"
            class="ratio-pill flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all">
            <span class="material-symbols-outlined text-base">crop_square</span>
            1:1 Square (1080×1080)
          </button>
          <button type="button" onclick="setGlobalRatio('16:9')" data-ratio-btn="16:9"
            class="ratio-pill flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all">
            <span class="material-symbols-outlined text-base">crop_16_9</span>
            16:9 Wide (1920×1080)
          </button>
          <button type="button" onclick="setGlobalRatio('9:16')" data-ratio-btn="9:16"
            class="ratio-pill flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all">
            <span class="material-symbols-outlined text-base">crop_portrait</span>
            9:16 Story (1080×1920)
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <!-- Interactive Ratio Preview Stage -->
        <div class="xl:col-span-7 bg-surface-container rounded-xl p-6 border border-slate-border flex flex-col items-center justify-center min-h-[540px]">
          <div class="w-full flex items-center justify-between mb-4">
            <span id="studio-dim-badge" class="px-2.5 py-1 rounded bg-surface-container-high font-mono text-xs text-primary">1920 × 1080 PX (16:9)</span>
            <span class="text-xs text-outline">Live rendered by Pillow compositor (`fwphotos.compose`)</span>
          </div>
          <div class="w-full flex items-center justify-center bg-surface-container-lowest rounded-xl p-6 border border-slate-border min-h-[440px]">
            <img id="studio-preview-img" src="/api/studio-preview?ratio=16:9" alt="Template Studio Preview"
              class="max-h-[420px] w-auto object-contain rounded-lg shadow-2xl border border-slate-border" />
          </div>
        </div>

        <!-- Template YAML Spec & Ratio Reference -->
        <div class="xl:col-span-5 bg-surface-container rounded-xl p-6 border border-slate-border flex flex-col gap-4">
          <h3 class="font-headline text-lg font-semibold text-on-surface">Configured Aspect-Ratio Profiles</h3>
          <div class="grid grid-cols-1 gap-3 text-xs">
            <div class="p-3.5 rounded-lg bg-surface-container-low border border-slate-border flex items-center justify-between">
              <div>
                <div class="font-mono font-bold text-primary">ratio_1_1 (Square 1:1)</div>
                <div class="text-outline mt-0.5">Instagram / Carousel Square Crop • Center-fit cover</div>
              </div>
              <span class="font-mono text-on-surface">1080 × 1080</span>
            </div>
            <div class="p-3.5 rounded-lg bg-surface-container-low border border-slate-border flex items-center justify-between">
              <div>
                <div class="font-mono font-bold text-primary">ratio_16_9 (Widescreen 16:9)</div>
                <div class="text-outline mt-0.5">Dealership Hero &amp; YouTube / Web Listing Banner</div>
              </div>
              <span class="font-mono text-on-surface">1920 × 1080</span>
            </div>
            <div class="p-3.5 rounded-lg bg-surface-container-low border border-slate-border flex items-center justify-between">
              <div>
                <div class="font-mono font-bold text-primary">ratio_9_16 (Vertical Story 9:16)</div>
                <div class="text-outline mt-0.5">IG Reels / TikTok / Stories Full-Screen Vertical</div>
              </div>
              <span class="font-mono text-on-surface">1080 × 1920</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script>
    let currentTab = 'upload';
    let currentRatio = '16:9';
    let appState = { cars_output: {}, cars_review: {} };
    let flatReviewList = [];
    let activeReviewIndex = 0;
    let manualPinsEnabled = false;
    let pinCoords = [
      { x: 35, y: 60 },
      { x: 65, y: 60 },
      { x: 65, y: 75 },
      { x: 35, y: 75 }
    ];

    function switchTab(tab) {
      currentTab = tab;
      document.querySelectorAll('.workspace-view').forEach(el => el.classList.add('hidden'));
      document.getElementById('view-' + tab).classList.remove('hidden');

      document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.className = 'nav-btn flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-on-surface-variant hover:bg-slate-elevated hover:text-on-surface transition-colors';
      });
      const activeBtn = document.getElementById('nav-' + tab);
      if (activeBtn) {
        activeBtn.className = 'nav-btn flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors bg-primary-container text-primary font-semibold border-l-2 border-primary';
      }
      if (tab === 'studio') {
        updateStudioPreview();
      }
    }

    function setGlobalRatio(ratio) {
      currentRatio = ratio;
      const dims = { '1:1': '1080×1080', '16:9': '1920×1080', '9:16': '1080×1920' };
      document.getElementById('sidebar-active-ratio').textContent = `${ratio} (${dims[ratio] || ''})`;
      const stageLbl = document.getElementById('review-stage-ratio-label');
      if (stageLbl) stageLbl.textContent = ratio;

      document.querySelectorAll('.ratio-pill').forEach(btn => {
        if (btn.getAttribute('data-ratio-btn') === ratio) {
          btn.classList.add('bg-primary-container', 'text-primary', 'border-lens-grid');
          btn.classList.remove('text-on-surface-variant');
        } else {
          btn.classList.remove('bg-primary-container', 'text-primary', 'border-lens-grid');
          btn.classList.add('text-on-surface-variant');
        }
      });

      document.querySelectorAll('.upload-ratio-btn').forEach(btn => {
        if (btn.getAttribute('data-upload-ratio') === ratio) {
          btn.className = 'upload-ratio-btn flex flex-col items-center justify-center py-2 px-2 rounded-lg border border-lens-grid bg-primary-container/60 text-primary transition-all';
        } else {
          btn.className = 'upload-ratio-btn flex flex-col items-center justify-center py-2 px-2 rounded-lg border border-slate-border bg-surface-container-lowest hover:bg-surface-container-high transition-all';
        }
      });

      renderGalleries();
      renderActiveReviewItem();
      if (currentTab === 'studio') {
        updateStudioPreview();
      }
    }

    function updateStudioPreview() {
      const dims = { '1:1': '1080 × 1080 PX (1:1)', '16:9': '1920 × 1080 PX (16:9)', '9:16': '1080 × 1920 PX (9:16)' };
      document.getElementById('studio-dim-badge').textContent = dims[currentRatio] || currentRatio;
      document.getElementById('studio-preview-img').src = `/api/studio-preview?ratio=${encodeURIComponent(currentRatio)}&t=${Date.now()}`;
    }

    async function handleFilesSelected(fileList) {
      if (!fileList || fileList.length === 0) return;
      const carId = (document.getElementById('upload-car-id').value || 'FW-BATCH').trim();
      const pill = document.getElementById('selected-files-pill');
      pill.textContent = `Uploading ${fileList.length} file(s) to ${carId} (${currentRatio})...`;
      pill.classList.remove('hidden');

      const progWrap = document.getElementById('upload-progress-wrap');
      progWrap.classList.remove('hidden');
      progWrap.classList.add('flex');

      const formData = new FormData();
      formData.append('car_id', carId);
      formData.append('ratio', currentRatio);
      for (let i = 0; i < fileList.length; i++) {
        formData.append('files', fileList[i]);
      }

      try {
        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (!resp.ok) {
          alert('Upload failed: ' + (data.detail || resp.statusText));
        } else {
          pill.textContent = `Processed ${data.processed_count} photo(s): ${data.output_count} to Output, ${data.review_count} to Review`;
          await refreshAllState();
          if (data.output_count > 0) {
            switchTab('galleries');
          } else if (data.review_count > 0) {
            switchTab('review');
          }
        }
      } catch (err) {
        alert('Upload error: ' + err);
      } finally {
        progWrap.classList.add('hidden');
        progWrap.classList.remove('flex');
      }
    }

    async function runDemoSampleBatch() {
      const carId = (document.getElementById('upload-car-id').value || 'FW-2026-911GT3').trim();
      const progWrap = document.getElementById('upload-progress-wrap');
      progWrap.classList.remove('hidden');
      progWrap.classList.add('flex');
      try {
        const resp = await fetch(`/api/demo-batch?car_id=${encodeURIComponent(carId)}&ratio=${encodeURIComponent(currentRatio)}`, { method: 'POST' });
        if (resp.ok) {
          await refreshAllState();
          switchTab('galleries');
        }
      } finally {
        progWrap.classList.add('hidden');
        progWrap.classList.remove('flex');
      }
    }

    async function refreshAllState() {
      const resp = await fetch('/api/state');
      if (!resp.ok) return;
      appState = await resp.json();

      // Count totals
      const outCars = Object.keys(appState.cars_output || {});
      let revTotal = 0;
      flatReviewList = [];
      Object.entries(appState.cars_review || {}).forEach(([cid, items]) => {
        items.forEach(item => {
          revTotal++;
          flatReviewList.push(item);
        });
      });

      document.getElementById('badge-galleries-count').textContent = outCars.length;
      document.getElementById('badge-review-count').textContent = revTotal;

      renderBatchesQueue();
      renderGalleries();
      renderReviewReel();
      renderActiveReviewItem();
    }

    function renderBatchesQueue() {
      const container = document.getElementById('batches-list');
      const allCarIds = new Set([
        ...Object.keys(appState.cars_output || {}),
        ...Object.keys(appState.cars_review || {})
      ]);
      document.getElementById('queue-batch-count').textContent = `${allCarIds.size} BATCH(ES)`;

      if (allCarIds.size === 0) {
        container.innerHTML = `<div class="p-6 text-center text-xs text-outline bg-surface-container-low rounded-lg border border-slate-border">No vehicle batches yet. Drop photos above or click "Process Test Photos Batch".</div>`;
        return;
      }

      const rows = [];
      allCarIds.forEach(cid => {
        const outItems = (appState.cars_output && appState.cars_output[cid]) || [];
        const revItems = (appState.cars_review && appState.cars_review[cid]) || [];
        const total = outItems.length + revItems.length;
        const pct = total > 0 ? Math.round((outItems.length / total) * 100) : 100;
        const label = cid === '_root' ? 'DEFAULT-BATCH' : cid;

        rows.push(`
          <div class="bg-surface-container-low hover:bg-surface-container-high border border-slate-border rounded-lg p-4 grid grid-cols-1 xl:grid-cols-12 gap-4 items-center transition-colors">
            <div class="xl:col-span-4 flex items-center gap-3">
              <div class="w-12 h-10 rounded bg-primary-container/60 border border-lens-grid/30 flex items-center justify-center font-mono text-xs text-primary font-bold">
                ${total}P
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-bold text-on-surface">${label}</span>
                  ${revItems.length > 0
                    ? `<span class="px-2 py-0.5 rounded bg-status-processing/20 text-status-processing text-[10px] font-bold uppercase">${revItems.length} Needs Review</span>`
                    : `<span class="px-2 py-0.5 rounded bg-lens-grid/15 text-lens-grid text-[10px] font-bold uppercase">Ready</span>`
                  }
                </div>
                <span class="text-xs text-outline font-mono">/output/${label}</span>
              </div>
            </div>
            <div class="xl:col-span-5 flex flex-col gap-1">
              <div class="flex justify-between text-xs">
                <span class="text-on-surface-variant">Plates Covered &amp; Cropped (${currentRatio})</span>
                <span class="font-mono text-primary font-semibold">${outItems.length} / ${total} Ready (${pct}%)</span>
              </div>
              <div class="w-full bg-surface-container-highest rounded-full h-2 overflow-hidden">
                <div class="bg-status-synced h-2 rounded-full" style="width:${pct}%"></div>
              </div>
            </div>
            <div class="xl:col-span-3 flex items-center justify-end gap-2">
              <button type="button" onclick="switchTab('galleries')" class="px-3 py-1.5 rounded bg-surface-container-high hover:bg-slate-elevated text-xs font-semibold text-primary flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">collections</span> Open Gallery
              </button>
              ${revItems.length > 0 ? `
                <button type="button" onclick="switchTab('review')" class="px-3 py-1.5 rounded bg-status-processing text-on-tertiary font-semibold text-xs flex items-center gap-1">
                  <span class="material-symbols-outlined text-sm">fact_check</span> Review (${revItems.length})
                </button>
              ` : ''}
            </div>
          </div>
        `);
      });
      container.innerHTML = rows.join('');
    }

    function renderGalleries() {
      const container = document.getElementById('galleries-container');
      const outMap = appState.cars_output || {};
      const cids = Object.keys(outMap);

      if (cids.length === 0) {
        container.innerHTML = `<div class="bg-surface-container rounded-xl p-10 text-center border border-slate-border">
          <span class="material-symbols-outlined text-4xl text-outline mb-2">photo_library</span>
          <h3 class="font-headline text-lg font-semibold">No Processed Vehicle Galleries Yet</h3>
          <p class="text-xs text-on-surface-variant mt-1">Upload car photos in the Upload Hub to generate plate-covered 1:1, 16:9, and 9:16 galleries.</p>
        </div>`;
        return;
      }

      const aspectCss = currentRatio === '1:1' ? 'aspect-square' : (currentRatio === '9:16' ? 'aspect-[9/16]' : 'aspect-video');

      container.innerHTML = cids.map(cid => {
        const items = outMap[cid] || [];
        const title = cid === '_root' ? 'General Processed Output' : cid;
        const thumbs = items.map(item => {
          const imgUrl = `/media/output/${encodeURIComponent(cid)}/${encodeURIComponent(item.filename)}?ratio=${encodeURIComponent(currentRatio)}`;
          const dlUrl = `${imgUrl}&download=1`;
          return `
            <div class="group relative rounded-xl overflow-hidden bg-surface-container-lowest border border-slate-border flex flex-col justify-between">
              <div class="relative w-full ${aspectCss} bg-black/40 overflow-hidden flex items-center justify-center">
                <img loading="lazy" src="${imgUrl}" alt="${item.filename}" class="w-full h-full object-contain transition-transform duration-300 group-hover:scale-105" />
                <div class="absolute top-2 left-2 px-2 py-0.5 rounded bg-surface-container-lowest/85 text-lens-grid font-mono text-[10px] font-semibold flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-status-synced"></span> Plate Masked • ${currentRatio}
                </div>
              </div>
              <div class="p-2.5 bg-surface-container flex items-center justify-between gap-2 border-t border-slate-border">
                <span class="text-xs font-mono truncate text-on-surface">${item.filename}</span>
                <a href="${dlUrl}" download="${cid}_${currentRatio.replace(':','x')}_${item.filename}"
                  class="px-2.5 py-1 rounded bg-primary-container hover:bg-secondary-container text-primary text-xs font-semibold flex items-center gap-1 shrink-0">
                  <span class="material-symbols-outlined text-sm">download</span> ${currentRatio}
                </a>
              </div>
            </div>
          `;
        }).join('');

        return `
          <section class="bg-surface-container-low rounded-xl p-6 border border-slate-border space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-border pb-4">
              <div>
                <div class="flex items-center gap-2">
                  <span class="px-2.5 py-0.5 rounded bg-primary-container text-primary font-mono text-xs font-bold">${title}</span>
                  <span class="px-2 py-0.5 rounded bg-surface-container-high text-status-synced text-[11px] font-mono">${items.length} Photo(s)</span>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <a href="/api/export/${encodeURIComponent(cid)}?ratio=${encodeURIComponent(currentRatio)}"
                  class="px-4 py-2 rounded-lg bg-primary-container hover:bg-secondary-container border border-lens-grid/40 text-primary text-xs font-semibold flex items-center gap-1.5 shadow-sm">
                  <span class="material-symbols-outlined text-base">folder_zip</span>
                  Download ${currentRatio} Batch (ZIP)
                </a>
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              ${thumbs}
            </div>
          </section>
        `;
      }).join('');
    }

    function renderReviewReel() {
      const reel = document.getElementById('review-reel-list');
      if (flatReviewList.length === 0) {
        reel.innerHTML = `<span class="text-xs text-outline">0 items pending</span>`;
        return;
      }
      if (activeReviewIndex >= flatReviewList.length) {
        activeReviewIndex = 0;
      }
      reel.innerHTML = flatReviewList.map((item, idx) => {
        const active = idx === activeReviewIndex;
        return `
          <button type="button" onclick="selectReviewItem(${idx})"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono shrink-0 border transition-all ${active ? 'bg-primary-container text-primary border-lens-grid' : 'bg-surface-container text-on-surface-variant border-slate-border'}">
            <span>#${idx + 1}</span>
            <span class="truncate max-w-[140px]">${item.filename}</span>
            <span class="px-1.5 py-0.2 rounded text-[10px] ${item.status === 'rejected' ? 'bg-error-container text-error' : 'bg-status-processing/20 text-status-processing'}">${item.status.toUpperCase()}</span>
          </button>
        `;
      }).join('');
    }

    function selectReviewItem(idx) {
      activeReviewIndex = idx;
      renderReviewReel();
      renderActiveReviewItem();
    }

    function renderActiveReviewItem() {
      const emptyMsg = document.getElementById('review-empty-msg');
      const beforeImg = document.getElementById('review-before-img');
      const afterClip = document.getElementById('review-after-clip');
      const afterImg = document.getElementById('review-after-img');
      const sliderHandle = document.getElementById('split-slider-handle');
      const badges = document.getElementById('review-badges');

      if (flatReviewList.length === 0) {
        emptyMsg.classList.remove('hidden');
        beforeImg.classList.add('hidden');
        afterClip.classList.add('hidden');
        sliderHandle.classList.add('hidden');
        badges.classList.add('hidden');
        document.getElementById('review-active-title').textContent = 'Queue Clear';
        document.getElementById('review-reason-pill').textContent = '0 Flagged';
        return;
      }

      const item = flatReviewList[activeReviewIndex];
      emptyMsg.classList.add('hidden');
      beforeImg.classList.remove('hidden');
      afterClip.classList.remove('hidden');
      sliderHandle.classList.remove('hidden');
      badges.classList.remove('hidden');

      document.getElementById('review-active-title').textContent = `${item.car_id === '_root' ? 'General' : item.car_id} / ${item.filename}`;
      document.getElementById('review-reason-pill').textContent = `Reason: ${item.reason}`;

      beforeImg.src = `/media/before/${encodeURIComponent(item.car_id)}/${encodeURIComponent(item.filename)}?t=${Date.now()}`;
      afterImg.src = `/media/after/${encodeURIComponent(item.car_id)}/${encodeURIComponent(item.filename)}?ratio=${encodeURIComponent(currentRatio)}&t=${Date.now()}`;
    }

    function setSplitPercent(pct) {
      const clamped = Math.max(0, Math.min(100, Number(pct)));
      document.getElementById('split-pct-label').textContent = `${Math.round(clamped)}%`;
      document.getElementById('split-range-input').value = clamped;
      document.getElementById('review-after-clip').style.clipPath = `polygon(${clamped}% 0, 100% 0, 100% 100%, ${clamped}% 100%)`;
      document.getElementById('split-slider-handle').style.left = `${clamped}%`;
    }

    function toggleManualPins() {
      manualPinsEnabled = !manualPinsEnabled;
      document.getElementById('pin-svg-layer').classList.toggle('hidden', !manualPinsEnabled);
      document.getElementById('pins-wrapper').classList.toggle('hidden', !manualPinsEnabled);
      document.getElementById('btn-toggle-pins').textContent = manualPinsEnabled ? 'Hide 4-Pin Overlay' : 'Show 4-Pin Overlay';
      updatePinPolygon();
    }

    function updatePinPolygon() {
      const pts = pinCoords.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      document.getElementById('pin-polygon').setAttribute('points', pts);
      pinCoords.forEach((p, idx) => {
        const el = document.getElementById('coord-p' + (idx + 1));
        if (el) el.textContent = `${Math.round(p.x)}% , ${Math.round(p.y)}%`;
      });
    }

    async function submitReviewDecision(action) {
      if (flatReviewList.length === 0) return;
      const item = flatReviewList[activeReviewIndex];
      const url = `/api/${action}/${encodeURIComponent(item.car_id)}/${encodeURIComponent(item.filename)}?ratio=${encodeURIComponent(currentRatio)}`;
      const body = manualPinsEnabled ? JSON.stringify({ quad_pct: pinCoords.map(p => [p.x, p.y]) }) : JSON.stringify({});

      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      });
      if (resp.ok) {
        await refreshAllState();
      } else {
        alert('Action failed: ' + resp.statusText);
      }
    }

    // Drag logic for split divider & 4 pins
    (function initInteractiveStage() {
      const stage = document.getElementById('inspector-stage');
      const divider = document.getElementById('split-slider-handle');
      let draggingDivider = false;
      let draggingPinIdx = null;

      divider.addEventListener('pointerdown', (e) => {
        draggingDivider = true;
        e.stopPropagation();
      });

      document.querySelectorAll('.pin-handle').forEach(el => {
        el.addEventListener('pointerdown', (e) => {
          draggingPinIdx = Number(el.getAttribute('data-pin'));
          e.stopPropagation();
        });
      });

      window.addEventListener('pointermove', (e) => {
        if (!draggingDivider && draggingPinIdx === null) return;
        const rect = stage.getBoundingClientRect();
        const xPct = Math.max(2, Math.min(98, ((e.clientX - rect.left) / rect.width) * 100));
        const yPct = Math.max(2, Math.min(98, ((e.clientY - rect.top) / rect.height) * 100));

        if (draggingDivider) {
          setSplitPercent(xPct);
        } else if (draggingPinIdx !== null) {
          pinCoords[draggingPinIdx] = { x: xPct, y: yPct };
          const pinEl = document.querySelector(`.pin-handle[data-pin="${draggingPinIdx}"]`);
          if (pinEl) {
            pinEl.style.left = `${xPct}%`;
            pinEl.style.top = `${yPct}%`;
          }
          updatePinPolygon();
        }
      });

      window.addEventListener('pointerup', () => {
        draggingDivider = false;
        draggingPinIdx = null;
      });

      window.addEventListener('keydown', (e) => {
        if (currentTab !== 'review' || flatReviewList.length === 0) return;
        if (e.target.tagName === 'INPUT') return;
        if (e.key === 'a' || e.key === 'A') submitReviewDecision('approve');
        if (e.key === 'r' || e.key === 'R') submitReviewDecision('reject');
      });
    })();

    // Initialize state on load
    refreshAllState();
  </script>
</body>
</html>
"""
