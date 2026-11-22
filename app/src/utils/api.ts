// Get API URL - use process.env for server-side (SSR), import.meta.env for client-side
// In Astro SSR, server-side code can access process.env, client-side uses import.meta.env
function getApiBaseUrl(): string {
	// Server-side (Node.js) - use process.env
	if (typeof process !== 'undefined' && process.env) {
		// If API_URL or PUBLIC_API_URL is explicitly set, use it
		if (process.env.API_URL) {
			return process.env.API_URL.trim();
		}
		if (process.env.PUBLIC_API_URL) {
			return process.env.PUBLIC_API_URL.trim();
		}
		// Otherwise, check if we're in Docker
		const isDocker = process.env.DOCKER === 'true';
		return isDocker ? 'http://api:4000' : 'http://localhost:4000';
	}
	// Client-side - use import.meta.env
	return (import.meta.env.PUBLIC_API_URL || 'http://localhost:4000').trim();
}

const API_BASE_URL = getApiBaseUrl();

export interface ServerInfo {
	name: string;
	instance_type?: string;
	ip_last_octet?: number;
	os_type?: string;
	roles?: string[];
	zeek?: boolean;
	zeek_monitor?: boolean;
}

export interface Template {
	name: string;
	provider: string;
	path: string;
	description?: string;
	provider_available?: boolean;
	architecture?: ServerInfo[];
}

export interface ProviderAvailability {
	provider: string;
	available: boolean;
	cli_command: string;
	error_message?: string;
}

export interface ProviderCheckResponse {
	providers: ProviderAvailability[];
}

export interface TemplateContent {
	name: string;
	provider: string;
	content: Record<string, any>;
}

export interface GuacamoleServer {
	name: string;
	protocol: string;
	hostname: string;
	port?: number;
	username?: string;
	password?: string;
}

export interface GuacamoleInfo {
	host_ip: string;
	servers: GuacamoleServer[];
}

export interface AttackRange {
	type: string;
	status: string;
	created_time: string;
	start_time?: string;
	end_time?: string;
	attack_range_id?: string;
	template_name?: string;
	router_public_ip?: string;
	wireguard_config?: string;
	wireguard_config_path?: string;
	sharing?: Record<string, string>;
	result?: {
		attack_range_id?: string;
		router_public_ip?: string;
		config_file?: string;
		architecture?: ServerInfo[];
		guacamole_info?: GuacamoleInfo;
		default_credentials?: Array<{ service: string; username: string; password: string; server?: string }>;
	};
	error?: string;
	error_phase?: string;
	traceback?: string;
}

export interface BuildRequest {
	template?: string;
	attack_range_id?: string;
}

export async function fetchTemplates(): Promise<{ templates: Template[]; providerAvailability: Record<string, ProviderAvailability> }> {
	const response = await fetch(`${API_BASE_URL}/templates`);
	if (!response.ok) {
		throw new Error('Failed to fetch templates');
	}
	const data = await response.json();
	return {
		templates: data.templates || [],
		providerAvailability: data.provider_availability || {}
	};
}

export async function checkProviders(): Promise<ProviderCheckResponse> {
	const response = await fetch(`${API_BASE_URL}/providers/check`);
	if (!response.ok) {
		throw new Error('Failed to check providers');
	}
	return await response.json();
}

export async function fetchTemplate(provider: string, name: string): Promise<TemplateContent> {
	const response = await fetch(`${API_BASE_URL}/templates/${provider}/${name}`);
	if (!response.ok) {
		throw new Error('Failed to fetch template');
	}
	return await response.json();
}

export async function fetchAttackRanges(): Promise<AttackRange[]> {
	const response = await fetch(`${API_BASE_URL}/attack-range/list`);
	if (!response.ok) {
		throw new Error('Failed to fetch attack ranges');
	}
	const data = await response.json();
	return data.attack_ranges || [];
}

export async function fetchAttackRangeStatus(attackRangeId: string): Promise<AttackRange> {
	const response = await fetch(`${API_BASE_URL}/attack-range/status/${attackRangeId}`);
	if (!response.ok) {
		throw new Error('Failed to fetch attack range status');
	}
	return await response.json();
}

export async function buildAttackRange(request: BuildRequest): Promise<{ status: string; message: string; attack_range_id: string; phase: string }> {
	const response = await fetch(`${API_BASE_URL}/attack-range/build`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.message || 'Failed to build attack range');
	}
	return await response.json();
}

export async function destroyAttackRange(attackRangeId: string): Promise<{ status: string; message: string }> {
	const response = await fetch(`${API_BASE_URL}/attack-range/destroy`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({ attack_range_id: attackRangeId }),
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.message || 'Failed to destroy attack range');
	}
	return await response.json();
}

export interface AtomicTestTarget {
	technique: string;
	guid: string;
}

export interface AtomicFileTarget {
	path?: string;
	content?: string;
	technique?: string;
	guid?: string;
	src_dir?: string;
}

export interface SimulateRequest {
	attack_range_id: string;
	target: string;
	techniques?: string[];
	atomics?: AtomicTestTarget[];
	atomic_files?: AtomicFileTarget[];
}

export interface SimulateResponse {
	status: string;
	message: string;
	attack_range_id: string;
	target: string;
	techniques: string[];
	atomics: AtomicTestTarget[];
	atomic_files?: AtomicFileTarget[];
	execution_status?: string | null;
	execution_summary?: AtomicExecutionSummary | null;
	execution_output?: AtomicExecutionOutput | null;
}

export interface AtomicExecutionSummary {
	total: number;
	succeeded: number;
	failed: number;
}

export interface AtomicExecutionResult {
	technique: string;
	guid: string;
	success: boolean;
	failed: boolean;
	return_code: number;
	stdout_lines: string[];
	stderr_lines: string[];
	stdout: string;
	stderr: string;
	error: string;
}

/** Mirrors _extract_atomic_simulation_output() in attack_range/managers/ansible_manager.py */
export interface AtomicExecutionOutput {
	status: string;
	summary: AtomicExecutionSummary;
	results: AtomicExecutionResult[];
	by_host: {
		[host: string]: {
			status: string;
			summary: AtomicExecutionSummary;
			results: AtomicExecutionResult[];
		};
	};
}

export interface SplunkExportRequest {
	attack_range_id: string;
	search: string;
	earliest_time?: string;
	latest_time?: string;
	max_results?: number;
}

export interface SplunkExportResponse {
	status: string;
	message: string;
	attack_range_id: string;
	search: string;
	earliest_time: string;
	latest_time: string;
	splunk_host: string;
	event_count: number;
	/** One Splunk _raw value per event */
	events: string[];
}

export async function exportSplunkEvents(request: SplunkExportRequest): Promise<SplunkExportResponse> {
	const response = await fetch(`${API_BASE_URL}/attack-range/splunk/export`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.message || error.details || 'Failed to export Splunk events');
	}
	return await response.json();
}

export async function simulateAttackRange(request: SimulateRequest): Promise<SimulateResponse> {
	const response = await fetch(`${API_BASE_URL}/attack-range/simulate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.message || 'Failed to run simulation');
	}
	return await response.json();
}

export interface ShareRequest {
	attack_range_id: string;
	name: string;
}

export interface ShareResponse {
	name: string;
	config: string;
	message: string;
}

export async function shareAttackRange(request: ShareRequest): Promise<ShareResponse> {
	const response = await fetch(`${API_BASE_URL}/attack-range/share`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.details || error.message || 'Failed to share attack range');
	}
	return await response.json();
}
