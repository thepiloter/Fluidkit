# Streaming Clients

FluidKit v0.2.4 adds first-class support for streaming endpoints with automatically generated TypeScript clients for Server-Sent Events, file downloads, and data streaming.

## Streaming Types

FluidKit detects streaming endpoints and generates appropriate TypeScript client patterns:

| Python Response | Generated Client | Use Case |
|----------------|------------------|----------|
| `EventSourceResponse` | EventSource API | Real-time updates, notifications |
| `StreamingResponse` (JSON) | ReadableStream | Large datasets, progressive loading |
| `StreamingResponse` (files) | Blob/download | File downloads, media streaming |
| `StreamingResponse` (text) | TextDecoder | Log streaming, text processing |

## Server-Sent Events (SSE)

### Python Implementation

```python
from sse_starlette import EventSourceResponse
from fastapi import APIRouter
import asyncio
import json

router = APIRouter()

@router.get("/notifications/stream")
async def stream_notifications(user_id: int):
    """Stream real-time notifications"""
    
    async def event_generator():
        while True:
            notifications = await get_user_notifications(user_id)
            
            for notification in notifications:
                yield {
                    "event": "notification",
                    "data": json.dumps(notification.dict())
                }
            
            await asyncio.sleep(1)
    
    return EventSourceResponse(event_generator())
```

### Usage in SvelteKit

```svelte
<script>
  import { stream_notifications } from './notifications.api';
  
  let notifications = $state([]);
  let connection = $state(null);
  let isConnected = $state(false);
  
  function startNotifications() {
    connection = stream_notifications(userId, {
      onMessage: (event) => {
        const notification = JSON.parse(event.data);
        notifications = [notification, ...notifications];
      },
      onOpen: () => {
        isConnected = true;
      },
      onError: (error) => {
        console.error('Connection error:', error);
        isConnected = false;
      }
    });
  }
  
  function stopNotifications() {
    if (connection) {
      connection.close();
      connection = null;
      isConnected = false;
    }
  }
</script>

<button onclick={startNotifications} disabled={isConnected}>
  Start Live Updates
</button>
<button onclick={stopNotifications} disabled={!isConnected}>
  Stop
</button>

{#if isConnected}
  <p class="status">🟢 Connected</p>
{/if}

{#each notifications as notification}
  <div class="notification">
    {notification.message}
  </div>
{/each}
```

## File Downloads

### Python Implementation

```python
from fastapi.responses import StreamingResponse
import aiofiles

@router.get("/files/{file_id}/download")
async def download_file(file_id: str):
    """Stream file download"""
    
    file_path = await get_file_path(file_id)
    
    async def file_streamer():
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := await file.read(8192):
                yield chunk
    
    return StreamingResponse(
        file_streamer(),
        media_type='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{file_path.name}"'}
    )
```

### Usage in SvelteKit

```svelte
<script>
  import { download_file } from './files.api';
  
  let downloading = $state(false);
  let error = $state('');
  
  async function handleDownload(fileId, filename) {
    downloading = true;
    error = '';
    
    try {
      const blob = await download_file(fileId);
      
      // Trigger download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      
      URL.revokeObjectURL(url);
    } catch (err) {
      error = 'Download failed';
    } finally {
      downloading = false;
    }
  }
</script>

<button onclick={() => handleDownload('123', 'report.pdf')} disabled={downloading}>
  {downloading ? 'Downloading...' : 'Download Report'}
</button>

{#if error}
  <p class="error">{error}</p>
{/if}
```

## JSON Data Streaming

### Python Implementation

```python
@router.get("/analytics/stream")
async def stream_analytics_data():
    """Stream large analytics dataset"""
    
    async def data_generator():
        async for batch in get_analytics_batches():
            for record in batch:
                yield json.dumps(record.dict()) + '\n'
    
    return StreamingResponse(
        data_generator(),
        media_type='application/x-ndjson'
    )
```

### Usage in SvelteKit

```svelte
<script>
  import { stream_analytics_data } from './analytics.api';
  
  let records = $state([]);
  let isStreaming = $state(false);
  let error = $state('');
  
  function startStreaming() {
    isStreaming = true;
    error = '';
    records = [];
    
    stream_analytics_data({
      onChunk: (record) => {
        records = [...records, record];
      },
      onError: (err) => {
        error = 'Streaming failed';
        isStreaming = false;
      },
      onComplete: () => {
        isStreaming = false;
      }
    });
  }
</script>

<button onclick={startStreaming} disabled={isStreaming}>
  {isStreaming ? 'Streaming...' : 'Load Analytics Data'}
</button>

{#if error}
  <p class="error">{error}</p>
{/if}

<div class="counter">Records loaded: {records.length}</div>

{#if records.length > 0}
  <div class="records">
    {#each records.slice(-5) as record}
      <div class="record">{record.name}: {record.value}</div>
    {/each}
  </div>
{/if}
```

## Benefits

- **Automatic Detection**: FluidKit detects streaming responses and generates appropriate clients
- **Type Safety**: Streaming callbacks maintain full TypeScript type safety
- **Environment Aware**: Same streaming clients work in SSR and browser contexts
- **Performance Optimized**: Efficient streaming patterns for large data and real-time updates
- **Clean APIs**: Generated clients abstract streaming complexity while maintaining control

Streaming support enables building responsive, real-time applications with Python backends and SvelteKit frontends.
