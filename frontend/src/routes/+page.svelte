<script lang="ts">
	import { ArrowLeft, ChevronRight, Copy, FileText, LoaderCircle, LogOut, NotebookPen, Plus, Search, Save, Trash2, X } from '@lucide/svelte';
	import { createUserWithEmailAndPassword, onAuthStateChanged, signInWithEmailAndPassword, signOut, type User } from 'firebase/auth';
	import { onMount } from 'svelte';
	import { firebaseAuth, firebaseConfigured } from '../lib/firebase';
	import { createNote, deleteNote, listNotes, updateNote, type Note } from '../lib/notes';

	let authReady = $state(false);
	let authUser = $state<User | null>(null);
	let authMode = $state<'signin' | 'signup'>('signin');
	let email = $state('');
	let password = $state('');
	let authBusy = $state(false);
	let authError = $state('');
	let notes = $state<Note[]>([]);
	let selectedId = $state<string | null>(null);
	let name = $state('');
	let subject = $state('');
	let search = $state('');
	let loading = $state(true);
	let saving = $state(false);
	let isCreating = $state(false);
	let showingList = $state(true);
	let errorMessage = $state('');
	let statusMessage = $state('');
	let tokenStatus = $state('');

	const selectedNote = $derived(notes.find((note) => note.id === selectedId));
	const filteredNotes = $derived.by(() => {
		const query = search.trim().toLocaleLowerCase();
		if (!query) return notes;
		return notes.filter((note) =>
			[note.name, note.subject, note.id].some((value) => value.toLocaleLowerCase().includes(query))
		);
	});
	const hasChanges = $derived(
		isCreating
			? Boolean(name.trim() || subject.trim())
			: Boolean(selectedNote && (name !== selectedNote.name || subject !== selectedNote.subject))
	);
	const canSave = $derived(Boolean(name.trim() && subject.trim() && hasChanges && !saving));

	onMount(() => {
		if (!firebaseAuth) {
			authReady = true;
			loading = false;
			return;
		}
		return onAuthStateChanged(firebaseAuth, (user) => {
			void handleAuthState(user);
		});
	});

	async function handleAuthState(user: User | null): Promise<void> {
		const accountChanged = authUser?.uid !== user?.uid;
		authUser = user;
		authReady = true;
		if (!user) {
			notes = [];
			selectedId = null;
			isCreating = false;
			showingList = true;
			loading = false;
			return;
		}
		if (accountChanged) {
			notes = [];
			selectedId = null;
			isCreating = false;
			showingList = true;
		}
		await loadNotes();
	}

	async function submitAuth(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (!firebaseAuth) return;
		authBusy = true;
		authError = '';
		try {
			if (authMode === 'signup') {
				await createUserWithEmailAndPassword(firebaseAuth, email.trim(), password);
			} else {
				await signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
			}
		} catch (error) {
			authError = error instanceof Error ? error.message : 'Authentication failed.';
		} finally {
			authBusy = false;
		}
	}

	async function logOut(): Promise<void> {
		if (!firebaseAuth) return;
		errorMessage = '';
		try {
			await signOut(firebaseAuth);
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Could not sign out.';
		}
	}

	async function copyMcpToken(): Promise<void> {
		tokenStatus = '';
		const user = authUser;
		if (!user) {
			tokenStatus = 'Sign in before copying an MCP token';
			return;
		}
		try {
			const token = await user.getIdToken();
			await navigator.clipboard.writeText(token);
			tokenStatus = 'Copied; expires in about 1 hour';
		} catch {
			tokenStatus = 'Clipboard unavailable; allow access and try again';
		}
	}

	async function loadNotes(): Promise<void> {
		loading = true;
		errorMessage = '';
		try {
			notes = await listNotes();
			if (!isCreating && !selectedId && notes.length > 0) {
				openNote(notes[0]);
			}
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Could not load notes.';
		} finally {
			loading = false;
		}
	}

	function canLeaveEditor(): boolean {
		return !hasChanges || window.confirm('Discard your unsaved changes?');
	}

	function openNote(note: Note): void {
		if (!canLeaveEditor()) return;
		selectedId = note.id;
		isCreating = false;
		name = note.name;
		subject = note.subject;
		statusMessage = '';
		showingList = false;
	}

	function startNewNote(): void {
		if (!canLeaveEditor()) return;
		selectedId = null;
		isCreating = true;
		name = '';
		subject = '';
		statusMessage = '';
		errorMessage = '';
		showingList = false;
	}

	function goToList(): void {
		showingList = true;
	}

	async function saveNote(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (!canSave) return;
		saving = true;
		errorMessage = '';
		statusMessage = '';
		try {
			const payload = { name: name.trim(), subject: subject.trim() };
			const saved = isCreating
				? await createNote(payload)
				: await updateNote(selectedId as string, payload);
			notes = [saved, ...notes.filter((note) => note.id !== saved.id)].sort(
				(left, right) => Date.parse(right.date) - Date.parse(left.date)
			);
			selectedId = saved.id;
			isCreating = false;
			name = saved.name;
			subject = saved.subject;
			statusMessage = 'Saved';
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Could not save this note.';
		} finally {
			saving = false;
		}
	}

	async function removeNote(): Promise<void> {
		if (!selectedNote || !window.confirm(`Delete “${selectedNote.name}”? This cannot be undone.`)) return;
		errorMessage = '';
		try {
			await deleteNote(selectedNote.id);
			notes = notes.filter((note) => note.id !== selectedNote.id);
			selectedId = null;
			if (notes.length > 0) {
				openNote(notes[0]);
			} else {
				isCreating = false;
				name = '';
				subject = '';
				showingList = true;
			}
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Could not delete this note.';
		}
	}

	function formatDate(value: string): string {
		return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(
			new Date(value)
		);
	}
</script>

<svelte:head>
	<title>Notes | Fieldnotes</title>
	<meta name="description" content="A quiet place to keep your notes." />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link
		href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

{#if !authReady}
	<div class="auth-page auth-loading"><LoaderCircle class="spin" size={22} /><span>Checking your session</span></div>
{:else if !firebaseConfigured}
	<div class="auth-page">
		<section class="auth-panel config-panel">
			<a class="auth-brand" href="/" aria-label="Fieldnotes home">
				<span class="brand-mark"><NotebookPen size={19} strokeWidth={1.8} /></span>
				<span>fieldnotes</span>
			</a>
			<div class="auth-heading">
				<p class="eyebrow">ACCOUNT SETUP</p>
				<h1>Authentication<br />isn’t configured.</h1>
				<p>Add this Firebase web app’s client configuration to the frontend environment to enable sign-in.</p>
			</div>
		</section>
	</div>
{:else if !authUser}
	<div class="auth-page">
		<section class="auth-panel">
			<a class="auth-brand" href="/" aria-label="Fieldnotes home">
				<span class="brand-mark"><NotebookPen size={19} strokeWidth={1.8} /></span>
				<span>fieldnotes</span>
			</a>
			<div class="auth-heading">
				<p class="eyebrow">YOUR PRIVATE LIBRARY</p>
				<h1>{authMode === 'signup' ? 'Make room for\nnew thoughts.' : 'Good to have\nyou back.'}</h1>
				<p>{authMode === 'signup' ? 'Create an account to start your own notes.' : 'Sign in to pick up where you left off.'}</p>
			</div>
			<div class="auth-tabs" role="tablist" aria-label="Account action">
				<button class:active={authMode === 'signin'} role="tab" aria-selected={authMode === 'signin'} onclick={() => { authMode = 'signin'; authError = ''; }}>Sign in</button>
				<button class:active={authMode === 'signup'} role="tab" aria-selected={authMode === 'signup'} onclick={() => { authMode = 'signup'; authError = ''; }}>Create account</button>
			</div>
			<form class="auth-form" onsubmit={submitAuth}>
				<label for="auth-email">Email</label>
				<input id="auth-email" type="email" bind:value={email} autocomplete="email" required />
				<label for="auth-password">Password</label>
				<input id="auth-password" type="password" bind:value={password} autocomplete={authMode === 'signup' ? 'new-password' : 'current-password'} minlength="6" required />
				{#if authError}<p class="auth-error" role="alert">{authError}</p>{/if}
				<button class="auth-submit" type="submit" disabled={authBusy}>
					{#if authBusy}<LoaderCircle class="spin" size={16} />{/if}
					<span>{authMode === 'signup' ? 'Create account' : 'Sign in'}</span>
				</button>
			</form>
			<p class="auth-footnote">Each account has its own private notes.</p>
		</section>
	</div>
{:else}
<div class="app-shell">
	<aside class="sidebar">
		<a class="brand" href="/" aria-label="Fieldnotes home">
			<span class="brand-mark"><NotebookPen size={19} strokeWidth={1.8} /></span>
			<span>fieldnotes</span>
		</a>

		<div class="sidebar-section-label">LIBRARY</div>
		<button class="new-note-button" onclick={startNewNote}>
			<Plus size={16} strokeWidth={2.2} />
			<span>New note</span>
		</button>
		<div class="sidebar-current">
			<FileText size={16} strokeWidth={1.8} />
			<span>All notes</span>
			<span class="note-count">{notes.length}</span>
		</div>

		<div class="sidebar-footer">
			<span class="connection-indicator"></span>
			<span class="signed-in-email">{authUser.email}</span>
		</div>
	</aside>

	<main class="main-area">
		<header class="topbar">
			<div class="breadcrumbs"><span>Workspace</span><ChevronRight size={14} /><strong>Notes</strong></div>
			<div class="topbar-actions">
				<label class="search-field">
					<Search size={16} strokeWidth={1.8} />
					<input bind:value={search} aria-label="Search notes" placeholder="Search notes" />
				</label>
				<button class="icon-button mobile-new-button" onclick={startNewNote} aria-label="Create note" title="Create note">
					<Plus size={18} />
				</button>
				<span class="account-email">{authUser.email}</span>
				{#if tokenStatus}<span class="mcp-token-status" role="status">{tokenStatus}</span>{/if}
				<button class="icon-button token-button" onclick={copyMcpToken} aria-label="Copy MCP token" title="Copy temporary MCP token">
					<Copy size={16} />
				</button>
				<button class="icon-button signout-button" onclick={logOut} aria-label="Sign out" title="Sign out">
					<LogOut size={17} />
				</button>
			</div>
		</header>

		<div class="workspace-grid" class:mobile-list={showingList}>
			<section class="notes-panel" aria-label="Notes list">
				<div class="panel-heading">
					<div>
						<p class="eyebrow">YOUR LIBRARY</p>
						<h1>Notes<span class="heading-period">.</span></h1>
					</div>
					<button class="icon-button panel-add-button" onclick={startNewNote} aria-label="Create note" title="Create note">
						<Plus size={18} />
					</button>
				</div>
				<div class="list-meta"><span>{notes.length} {notes.length === 1 ? 'note' : 'notes'}</span><span class="meta-line"></span><span>Newest first</span></div>

				{#if loading}
					<div class="list-state"><LoaderCircle class="spin" size={19} /><span>Loading notes</span></div>
				{:else if filteredNotes.length === 0}
					<div class="list-state empty-list">
						<FileText size={19} strokeWidth={1.6} />
						<span>{search ? 'No matching notes' : 'No notes yet'}</span>
					</div>
				{:else}
					<div class="note-list">
						{#each filteredNotes as note (note.id)}
							<button
								class="note-row"
								class:selected={selectedId === note.id && !isCreating}
								onclick={() => openNote(note)}
							>
								<span class="note-row-top"><span class="note-row-title">{note.name}</span><span class="note-row-date">{formatDate(note.date)}</span></span>
								<span class="note-row-preview">{note.subject}</span>
							</button>
						{/each}
					</div>
				{/if}
			</section>

			<section class="editor-panel" aria-label="Note editor">
				{#if selectedNote || isCreating}
					<div class="editor-toolbar">
						<button class="back-button" onclick={goToList} aria-label="Back to notes"><ArrowLeft size={17} /><span>Notes</span></button>
						<div class="editor-toolbar-right">
							{#if statusMessage}<span class="saved-status">{statusMessage}</span>{/if}
							{#if selectedNote}
								<button class="icon-button delete-button" onclick={removeNote} aria-label="Delete note" title="Delete note"><Trash2 size={17} /></button>
							{/if}
							<button class="save-button" form="note-form" type="submit" disabled={!canSave}>
								{#if saving}<LoaderCircle class="spin" size={15} />{:else}<Save size={15} />{/if}
								<span>{isCreating ? 'Create note' : 'Save changes'}</span>
							</button>
						</div>
					</div>

					<div class="editor-scroll">
						{#if errorMessage}
							<div class="alert" role="alert"><span class="alert-dot"></span>{errorMessage}</div>
						{/if}
						<form id="note-form" class="note-form" onsubmit={saveNote}>
							<label class="field-label" for="note-name">NAME</label>
							<input id="note-name" class="title-input" bind:value={name} maxlength="120" placeholder="Untitled note" autocomplete="off" />
							<div class="date-line">
								<span class="date-dot"></span>
								<span>{selectedNote ? `Created ${formatDate(selectedNote.date)}` : 'Date is set when you create this note'}</span>
							</div>
							<div class="subject-divider"></div>
							<label class="field-label" for="note-subject">SUBJECT</label>
							<textarea id="note-subject" class="subject-input" bind:value={subject} maxlength="20000" placeholder="Write something worth remembering…"></textarea>
							<div class="editor-bottom-line"><span>{subject.length.toLocaleString()} / 20,000</span><span>{hasChanges ? 'Unsaved changes' : 'All changes saved'}</span></div>
						</form>
					</div>
				{:else if loading}
					<div class="editor-empty loading-empty"><LoaderCircle class="spin" size={22} /><span>Opening your notes</span></div>
				{:else if errorMessage}
					<div class="editor-empty error-empty">
						<div class="error-mark"><X size={18} /></div>
						<h2>Notes could not load</h2>
						<p>{errorMessage}</p>
						<button class="save-button" onclick={loadNotes}><span>Try again</span></button>
					</div>
				{:else}
					<div class="editor-empty welcome-empty">
						<div class="empty-mark"><NotebookPen size={23} strokeWidth={1.5} /></div>
						<p class="eyebrow">A PLACE TO BEGIN</p>
						<h2>A blank page<br />is full of possibility.</h2>
						<p class="empty-copy">Start with a thought, a detail, or a question you want to keep.</p>
						<button class="save-button" onclick={startNewNote}><Plus size={16} /><span>Write your first note</span></button>
					</div>
				{/if}
			</section>
		</div>
	</main>
</div>
{/if}
