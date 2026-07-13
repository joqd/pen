<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
</script>

{#if data.user}
	<h1>Hello {data.user.phone}</h1>
	<p>You are login.</p>

	<a class="text-blue-500" href={resolve('/auth/logout')}>Logout</a>
{:else}
	<h1>You are not login.</h1>

	<a class="text-blue-500" href={resolve('/auth')}>Login</a>
{/if}
