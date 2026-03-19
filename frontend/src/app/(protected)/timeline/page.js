"use client";

import { apiFetch } from "@/lib/api";
import { useEffect, useRef, useState, useCallback } from "react";
import EmptyState from "@/components/empty-state";
import {
  PhotoIcon,
  PlusIcon,
  CameraIcon,
  TrashIcon,
  PencilIcon,
  FolderIcon,
  ArrowLeftIcon,
  CheckIcon,
} from "@/components/icons";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "photos", label: "Photos" },
  { value: "notes", label: "Notes" },
];

// ---------------------------------------------------------------------------
// Fullscreen image lightbox
// ---------------------------------------------------------------------------
function Lightbox({ src, alt, onClose }) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white/70 hover:text-white text-3xl font-light z-10"
        aria-label="Close"
      >
        &times;
      </button>
      <img
        src={src}
        alt={alt || "Full size image"}
        className="max-h-[90vh] max-w-[90vw] object-contain rounded-lg"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Camera capture modal
// ---------------------------------------------------------------------------
function CameraCapture({ onCapture, onClose }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fallbackRef = useRef(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => setReady(true);
        }
      } catch {
        // getUserMedia failed — use native camera fallback (works on iPhone)
        setError("native-fallback");
      }
    }
    start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  function handleSnap() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], `camera-${Date.now()}.jpg`, {
            type: "image/jpeg",
          });
          onCapture(file);
        }
      },
      "image/jpeg",
      0.9
    );
  }

  function handleFallbackChange(e) {
    const file = e.target.files?.[0];
    if (file) onCapture(file);
  }

  // Native camera fallback for iOS / browsers that block getUserMedia
  if (error === "native-fallback") {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
        <div className="relative w-full max-w-md rounded-xl bg-zinc-900 p-6 space-y-4 text-center">
          <h3 className="text-sm font-medium text-white">Take a Photo</h3>
          <p className="text-xs text-zinc-400">
            Camera preview isn&apos;t available in this browser. Tap below to open your camera.
          </p>
          <label className="inline-block cursor-pointer rounded-lg bg-pink-600 px-6 py-3 text-sm font-medium text-white hover:bg-pink-500">
            Open Camera
            <input
              ref={fallbackRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFallbackChange}
            />
          </label>
          <button
            onClick={onClose}
            className="block mx-auto text-xs text-zinc-400 hover:text-white mt-2"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
      <div className="relative w-full max-w-md rounded-xl bg-zinc-900 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-white">Camera</h3>
          <button
            onClick={onClose}
            className="text-xs text-zinc-400 hover:text-white"
          >
            Close
          </button>
        </div>

        {error ? (
          <p className="text-sm text-red-400 py-8 text-center">{error}</p>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full rounded-lg bg-black aspect-video object-cover"
          />
        )}

        {!error && (
          <button
            onClick={handleSnap}
            disabled={!ready}
            className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border-4 border-white bg-transparent transition-colors hover:bg-white/10 disabled:opacity-40"
          >
            <div className="h-10 w-10 rounded-full bg-white" />
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Upload composer (preview + caption + optional album)
// ---------------------------------------------------------------------------
function UploadComposer({ file, albums, onSubmit, onCancel }) {
  const [caption, setCaption] = useState("");
  const [albumId, setAlbumId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const previewUrl = useRef(null);

  if (!previewUrl.current && file) {
    previewUrl.current = URL.createObjectURL(file);
  }

  useEffect(() => {
    const url = previewUrl.current;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await onSubmit(file, caption, albumId || null);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-3"
    >
      {previewUrl.current && (
        <img
          src={previewUrl.current}
          alt="Preview"
          className="w-full max-h-64 rounded-lg object-cover"
        />
      )}
      <input
        type="text"
        value={caption}
        onChange={(e) => setCaption(e.target.value)}
        placeholder="Add a caption…"
        className="w-full bg-transparent text-white text-sm placeholder-zinc-500 outline-none"
      />
      {albums.length > 0 && (
        <select
          value={albumId}
          onChange={(e) => setAlbumId(e.target.value)}
          className="w-full rounded-md bg-zinc-800 px-3 py-2 text-sm text-white border border-zinc-700 outline-none"
        >
          <option value="">No album (standalone)</option>
          {albums.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      )}
      <div className="flex items-center gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-3 py-1.5 text-xs text-zinc-400 hover:text-white"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
        >
          {submitting ? "Uploading…" : "Upload"}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  );
}

// ---------------------------------------------------------------------------
// Create album modal
// ---------------------------------------------------------------------------
function CreateAlbumModal({ onCreated, onClose }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await apiFetch("/albums/", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), description: description.trim() }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Failed to create album.");
      }
      const album = await res.json();
      onCreated(album);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl bg-zinc-900 border border-zinc-800 p-5 space-y-4"
      >
        <h3 className="text-base font-semibold text-white">New Album</h3>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Album title (e.g. Paris Trip)"
          className="w-full rounded-md bg-zinc-800 px-3 py-2 text-sm text-white placeholder-zinc-500 border border-zinc-700 outline-none focus:border-zinc-500"
          autoFocus
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          rows={2}
          className="w-full rounded-md bg-zinc-800 px-3 py-2 text-sm text-white placeholder-zinc-500 border border-zinc-700 outline-none focus:border-zinc-500 resize-none"
        />
        <div className="flex items-center gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-3 py-1.5 text-xs text-zinc-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !title.trim()}
            className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create Album"}
          </button>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Album card
// ---------------------------------------------------------------------------
function AlbumCard({ album, onClick }) {
  return (
    <button
      onClick={onClick}
      className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50 text-left transition-colors hover:border-zinc-600 w-full"
    >
      {album.cover ? (
        <img
          src={album.cover}
          alt={album.title}
          className="w-full aspect-video object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full aspect-video bg-zinc-800 flex items-center justify-center">
          <FolderIcon className="h-10 w-10 text-zinc-600" />
        </div>
      )}
      <div className="p-3 space-y-1">
        <p className="text-sm font-medium text-white">{album.title}</p>
        <p className="text-[10px] text-zinc-500">
          {album.photo_count} photo{album.photo_count !== 1 ? "s" : ""} ·{" "}
          {album.created_by_name}
        </p>
        {album.description && (
          <p className="text-xs text-zinc-400 line-clamp-2">{album.description}</p>
        )}
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Album detail view
// ---------------------------------------------------------------------------
function AlbumDetailView({ album: initialAlbum, onBack, onDeleted }) {
  const [album, setAlbum] = useState(initialAlbum);
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const fileInputRef = useRef(null);

  const loadAlbum = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/albums/${album.id}/`);
      if (res.ok) {
        const data = await res.json();
        setAlbum(data);
        setPhotos(data.photos || []);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [album.id]);

  useEffect(() => {
    loadAlbum();
  }, [loadAlbum]);

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
    e.target.value = "";
  }

  function handleCameraCapture(file) {
    setShowCamera(false);
    setSelectedFile(file);
  }

  async function handleUpload(file, caption) {
    const form = new FormData();
    form.append("image", file);
    if (caption) form.append("caption", caption);
    form.append("album_id", album.id);

    const res = await apiFetch("/memories/", {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || d.image?.[0] || "Upload failed.");
    }
    const created = await res.json();
    setPhotos((prev) => [created, ...prev]);
    setSelectedFile(null);
  }

  async function handleDeleteAlbum() {
    if (!confirm("Delete this album? Photos will be kept but unlinked.")) return;
    setDeleting(true);
    try {
      const res = await apiFetch(`/albums/${album.id}/`, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        onDeleted(album.id);
      }
    } catch { /* ignore */ }
    setDeleting(false);
  }

  async function handleRemovePhoto(memoryId) {
    const res = await apiFetch(`/albums/${album.id}/remove-photos/`, {
      method: "POST",
      body: JSON.stringify({ memory_ids: [memoryId] }),
    });
    if (res.ok) {
      setPhotos((prev) => prev.filter((p) => p.id !== memoryId));
    }
  }

  const hasCamera =
    typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  return (
    <div className="flex flex-1 flex-col space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center justify-center rounded-md border border-zinc-700 p-1.5 text-zinc-400 hover:text-white hover:border-zinc-500"
        >
          <ArrowLeftIcon className="h-4 w-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold truncate">{album.title}</h1>
          {album.description && (
            <p className="mt-0.5 text-sm text-zinc-400 line-clamp-1">{album.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {!selectedFile && (
            <>
              {hasCamera && (
                <button
                  onClick={() => setShowCamera(true)}
                  className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:border-zinc-500 hover:text-white"
                >
                  <CameraIcon className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200"
              >
                <PlusIcon className="h-3.5 w-3.5" />
                Add
              </button>
            </>
          )}
          <button
            onClick={handleDeleteAlbum}
            disabled={deleting}
            className="flex items-center gap-1.5 rounded-md border border-red-800/50 px-3 py-1.5 text-xs text-red-400 hover:border-red-600 hover:text-red-300 disabled:opacity-50"
          >
            <TrashIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
        className="hidden"
        onChange={handleFileChange}
      />

      {showCamera && (
        <CameraCapture
          onCapture={handleCameraCapture}
          onClose={() => setShowCamera(false)}
        />
      )}

      {selectedFile && (
        <UploadComposer
          file={selectedFile}
          albums={[]}
          onSubmit={handleUpload}
          onCancel={() => setSelectedFile(null)}
        />
      )}

      {loading ? (
        <p className="text-sm text-zinc-500">Loading photos…</p>
      ) : photos.length === 0 && !selectedFile ? (
        <EmptyState
          icon={<PhotoIcon className="h-7 w-7" />}
          title="No photos yet"
          description="Add photos to this album to start your collection."
          actionLabel="Add a photo"
          onAction={() => fileInputRef.current?.click()}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50"
            >
              <img
                src={photo.thumbnail || photo.image}
                alt={photo.caption || "Photo"}
                className="w-full aspect-square object-cover cursor-pointer"
                loading="lazy"
                onClick={() => setLightboxSrc(photo.image)}
              />
              {photo.caption && (
                <div className="p-2">
                  <p className="text-xs text-zinc-300 line-clamp-1">{photo.caption}</p>
                </div>
              )}
              <button
                onClick={() => handleRemovePhoto(photo.id)}
                className="absolute top-2 right-2 rounded-md bg-black/60 p-1 text-zinc-400 opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
                title="Remove from album"
              >
                <TrashIcon className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {lightboxSrc && (
        <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Timeline items
// ---------------------------------------------------------------------------
function PhotoItem({ item }) {
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const c = item.content;
  return (
    <>
      <div className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50">
        <img
          src={c.thumbnail || c.image}
          alt={c.caption || "Memory"}
          className="w-full aspect-video object-cover cursor-pointer"
          loading="lazy"
          onClick={() => setLightboxSrc(c.image)}
        />
        <div className="p-3 space-y-1">
          {c.caption && (
            <p className="text-sm text-white">{c.caption}</p>
          )}
          <p className="text-[10px] text-zinc-500">
            {item.actor} · {new Date(item.timestamp).toLocaleDateString()}
          </p>
        </div>
      </div>
      {lightboxSrc && (
        <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}
    </>
  );
}

function NoteItem({ item }) {
  const c = item.content;
  const isOpenWhen = c.open_when_type && c.open_when_type !== "normal";

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-2">
      <div className="flex items-center gap-2 text-zinc-400">
        <PencilIcon className="h-3.5 w-3.5" />
        <span className="text-[10px] uppercase tracking-wider font-medium">Note</span>
        {c.is_pinned && <span className="text-[10px]">📌</span>}
        {isOpenWhen && (
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
            {c.open_when_type.replace(/_/g, " ")}
          </span>
        )}
      </div>
      {c.title && (
        <p className="text-sm font-medium text-white">{c.title}</p>
      )}
      <p className="text-sm text-zinc-300 whitespace-pre-wrap line-clamp-4">{c.body}</p>
      <p className="text-[10px] text-zinc-500">
        {item.actor} · {new Date(item.timestamp).toLocaleDateString()}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function TimelinePage() {
  const [items, setItems] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [selectedFile, setSelectedFile] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [showCreateAlbum, setShowCreateAlbum] = useState(false);
  const [activeAlbum, setActiveAlbum] = useState(null);
  const [view, setView] = useState("timeline"); // "timeline" | "albums"
  const fileInputRef = useRef(null);

  // Load timeline
  useEffect(() => {
    if (view !== "timeline") return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const res = await apiFetch(`/timeline/?type=${filter}`);
        if (res.ok && !cancelled) setItems(await res.json());
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [filter, view]);

  // Load albums
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await apiFetch("/albums/");
        if (res.ok && !cancelled) setAlbums(await res.json());
      } catch { /* ignore */ }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
    e.target.value = "";
  }

  function handleCameraCapture(file) {
    setShowCamera(false);
    setSelectedFile(file);
  }

  async function handleUpload(file, caption, albumId) {
    const form = new FormData();
    form.append("image", file);
    if (caption) form.append("caption", caption);
    if (albumId) form.append("album_id", albumId);

    const res = await apiFetch("/memories/", {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || d.image?.[0] || "Upload failed.");
    }
    const created = await res.json();
    // Prepend as a timeline item
    const newItem = {
      id: `memory-${created.id}`,
      type: "photo",
      timestamp: created.created_at,
      actor: created.uploaded_by_name,
      content: {
        id: created.id,
        caption: created.caption,
        image: created.image,
        thumbnail: created.thumbnail,
      },
    };
    setItems((prev) => [newItem, ...prev]);
    setSelectedFile(null);
  }

  function handleAlbumCreated(album) {
    setAlbums((prev) => [album, ...prev]);
    setShowCreateAlbum(false);
  }

  function handleAlbumDeleted(albumId) {
    setAlbums((prev) => prev.filter((a) => a.id !== albumId));
    setActiveAlbum(null);
  }

  const hasCamera =
    typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  // Viewing a specific album
  if (activeAlbum) {
    return (
      <AlbumDetailView
        album={activeAlbum}
        onBack={() => setActiveAlbum(null)}
        onDeleted={handleAlbumDeleted}
      />
    );
  }

  return (
    <div className="flex flex-1 flex-col space-y-6">
      {/* Header */}
      <div className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">Timeline</h1>
          <p className="mt-1 text-sm text-zinc-400">Your shared moments</p>
        </div>
        {!selectedFile && (
          <div className="flex gap-2 overflow-x-auto">
            <button
              onClick={() => setShowCreateAlbum(true)}
              className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:border-zinc-500 hover:text-white shrink-0"
            >
              <FolderIcon className="h-3.5 w-3.5" />
              New Album
            </button>
            {hasCamera && (
              <button
                onClick={() => setShowCamera(true)}
                className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:border-zinc-500 hover:text-white shrink-0"
              >
                <CameraIcon className="h-3.5 w-3.5" />
                Camera
              </button>
            )}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 shrink-0"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Upload
            </button>
          </div>
        )}
      </div>

      {/* View toggle + filters */}
      <div className="flex items-center gap-3">
        <div className="flex gap-1 rounded-lg bg-zinc-800/50 p-0.5">
          <button
            onClick={() => setView("timeline")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              view === "timeline"
                ? "bg-zinc-700 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Timeline
          </button>
          <button
            onClick={() => setView("albums")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              view === "albums"
                ? "bg-zinc-700 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Albums{albums.length > 0 ? ` (${albums.length})` : ""}
          </button>
        </div>
        {view === "timeline" && (
          <div className="flex gap-1">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filter === f.value
                    ? "bg-white text-black"
                    : "bg-zinc-800 text-zinc-400 hover:text-white"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Camera modal */}
      {showCamera && (
        <CameraCapture
          onCapture={handleCameraCapture}
          onClose={() => setShowCamera(false)}
        />
      )}

      {/* Create album modal */}
      {showCreateAlbum && (
        <CreateAlbumModal
          onCreated={handleAlbumCreated}
          onClose={() => setShowCreateAlbum(false)}
        />
      )}

      {/* Upload composer */}
      {selectedFile && (
        <UploadComposer
          file={selectedFile}
          albums={albums}
          onSubmit={handleUpload}
          onCancel={() => setSelectedFile(null)}
        />
      )}

      {/* Albums view */}
      {view === "albums" && (
        <>
          {albums.length === 0 ? (
            <EmptyState
              icon={<FolderIcon className="h-7 w-7" />}
              title="No albums yet"
              description="Create albums to organize your photos into trips, events, and collections."
              actionLabel="Create an Album"
              onAction={() => setShowCreateAlbum(true)}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {albums.map((album) => (
                <AlbumCard
                  key={album.id}
                  album={album}
                  onClick={() => setActiveAlbum(album)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Timeline view */}
      {view === "timeline" && (
        <>
          {loading ? (
            <p className="text-sm text-zinc-500">Loading timeline…</p>
          ) : items.length === 0 && !selectedFile ? (
            <EmptyState
              icon={<PhotoIcon className="h-7 w-7" />}
              title="Your timeline is empty"
              description="Upload photos or write notes to start building your shared timeline."
              actionLabel="Upload a photo"
              onAction={() => fileInputRef.current?.click()}
            />
          ) : (
            <div className="space-y-4">
              {items.map((item) =>
                item.type === "photo" ? (
                  <PhotoItem key={item.id} item={item} />
                ) : (
                  <NoteItem key={item.id} item={item} />
                )
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
