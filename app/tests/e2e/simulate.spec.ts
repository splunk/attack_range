import { test, expect } from '@playwright/test';

// Response shape returned by POST /attack-range/simulate (see api/models.py SimulateResponse
// and _extract_atomic_simulation_output in attack_range/managers/ansible_manager.py).
const simulateResponse = {
	status: 'success',
	message: 'Successfully executed 1 technique(s) on Splunk',
	attack_range_id: 'test-123',
	target: 'Splunk',
	techniques: ['T1197'],
	atomics: [],
	atomic_files: [],
	execution_status: 'success',
	execution_summary: { total: 1, succeeded: 1, failed: 0 },
	execution_output: {
		results: [
			{
				technique: 'T1197',
				guid: '',
				success: true,
				failed: false,
				return_code: 0,
				stdout_lines: ['Executing test: T1197-1 Bitsadmin Download (cmd)', '<script>not-html</script>'],
				stderr_lines: [],
				stdout: '',
				stderr: '',
				error: '',
			},
		],
		status: 'success',
		summary: { total: 1, succeeded: 1, failed: 0 },
		by_host: {
			'10.0.2.10': {
				status: 'success',
				summary: { total: 1, succeeded: 1, failed: 0 },
				results: [
					{
						technique: 'T1197',
						guid: '',
						success: true,
						failed: false,
						return_code: 0,
						stdout_lines: ['Executing test: T1197-1 Bitsadmin Download (cmd)', '<script>not-html</script>'],
						stderr_lines: [],
						stdout: '',
						stderr: '',
						error: '',
					},
				],
			},
		},
	},
};

test('simulation result renders structured execution output', async ({ page }) => {
	await page.route('**/attack-range/simulate', (route) =>
		route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(simulateResponse) }),
	);

	await page.goto('/attack-ranges/test-123');
	await page.selectOption('#target-server', 'Splunk');
	await page.fill('#techniques', 'T1197');
	await page.click('#simulate-button');

	const result = page.locator('#simulation-result');
	await expect(result).toBeVisible();
	await expect(result).toContainText('Simulation Completed Successfully');
	await expect(result).not.toContainText('Simulation Failed');
	await expect(result).toContainText('Host: 10.0.2.10');
	await expect(result).toContainText('Technique: T1197 — succeeded');
	await expect(result).toContainText('1/1 succeeded');
	await expect(result.locator('pre.output-lines')).toContainText('Bitsadmin Download');
	// Atomic output must be rendered as text, not injected as HTML
	await expect(result.locator('pre.output-lines')).toContainText('<script>not-html</script>');
});
