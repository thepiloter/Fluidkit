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
            # Get notifications from database/queue
            notifications = await get_user_notifications(user_id)
            
            for notification in notifications:
                yield {
                    "event": "notification",
                    "data": json.dumps(notification.dict())
                }
            
            await asyncio.sleep(1)  # Poll interval
    
    return EventSourceResponse(event_generator())
```

### Generated TypeScript Client

```typescript
import type { SSECallbacks, SSEConnection } from './.fluidkit/runtime';

/**
 * Stream real-time notifications
 * Server-Sent Events endpoint
 */
export const stream_notifications = (
  user_id: number,
  callbacks: SSECallbacks,
  options?: SSERequestInit
): SSEConnection => {
  const url = `${getBaseUrl()}/notifications/stream?user_id=${user_id}`;
  
  const eventSource = new EventSource(url);
  
  if (callbacks.onMessage) {
    eventSource.addEventListener('message', callbacks.onMessage);
  }
  if (callbacks.onError) {
    eventSource.addEventListener('error', callbacks.onError);
  }
  if (callbacks.onOpen) {
    eventSource.addEventListener('open', callbacks.onOpen);
  }
  
  return eventSource;
};
```

### Usage in SvelteKit

```svelte
<script>
  import { stream_notifications } from './notifications.api';
  
  let notifications = [];
  let connection = null;
  
  function startNotifications() {
    connection = stream_notifications(userId, {
      onMessage: (event) => {
        const notification = JSON.parse(event.data);
        notifications = [notification, ...notifications];
      },
      onError: (error) => {
        console.error('Connection error:', error);
      }
    });
  }
  
  function stopNotifications() {
    if (connection) {
      connection.close();
      connection = null;
    }
  }
</script>

<button on:click={startNotifications}>Start Live Updates</button>
<button on:click={stopNotifications}>Stop</button>

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
from fastapi import APIRouter
import aiofiles

router = APIRouter()

@router.get("/files/{file_id}/download")
async def download_file(file_id: str):
    """Stream file download"""
    
    file_path = await get_file_path(file_id)
    file_size = await get_file_size(file_path)
    
    async def file_streamer():
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := await file.read(8192):
                yield chunk
    
    return StreamingResponse(
        file_streamer(),
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{file_path.name}"',
            'Content-Length': str(file_size)
        }
    )
```

### Generated TypeScript Client

```typescript
/**
 * Stream file download
 * File download endpoint
 */
export const download_file = async (
  file_id: string,
  options?: RequestInit
): Promise<Blob> => {
  const url = `${getBaseUrl()}/files/${file_id}/download`;
  
  const response = await fetch(url, {
    method: 'GET',
    ...options
  });
  
  if (!response.ok) {
    throw new Error(`Download failed: ${response.statusText}`);
  }
  
  return response.blob();
};
```

### Usage in SvelteKit

```svelte
<script>
  import { download_file } from './files.api';
  
  async function handleDownload(fileId, filename) {
    try {
      const blob = await download_file(fileId);
      
      // Create download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  }
</script>

<button on:click={() => handleDownload('123', 'report.pdf')}>
  Download Report
</button>
```

## JSON Data Streaming

### Python Implementation

```python
from fastapi.responses import StreamingResponse
import json

@router.get("/analytics/stream")
async def stream_analytics_data():
    """Stream large analytics dataset"""
    
    async def data_generator():
        # Stream large dataset in chunks
        async for batch in get_analytics_batches():
            for record in batch:
                yield json.dumps(record.dict()) + '\n'
    
    return StreamingResponse(
        data_generator(),
        media_type='application/x-ndjson'
    )
```

### Generated TypeScript Client

```typescript
/**
 * Stream large analytics dataset
 * JSON streaming endpoint
 */
export const stream_analytics_data = async (
  callbacks: StreamingCallbacks<AnalyticsRecord>,
  options?: RequestInit
): Promise<void> => {
  const url = `${getBaseUrl()}/analytics/stream`;
  
  const response = await fetch(url, { method: 'GET', ...options });
  
  if (!response.ok) {
    throw new Error(`Streaming failed: ${response.statusText}`);
  }
  
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  try {
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      
      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const record = JSON.parse(line);
          callbacks.onChunk?.(record);
        } catch (e) {
          callbacks.onError?.(new Error(`Invalid JSON: ${line}`));
        }
      }
    }
    callbacks.onComplete?.();
  } catch (error) {
    callbacks.onError?.(error);
  }
};
```

### Usage in SvelteKit

```svelte
<script>
  import { stream_analytics_data } from './analytics.api';
  
  let records = [];
  let isStreaming = false;
  
  async function startStreaming() {
    isStreaming = true;
    records = [];
    
    await stream_analytics_data({
      onChunk: (record) => {
        records = [...records, record];
      },
      onError: (error) => {
        console.error('Streaming error:', error);
        isStreaming = false;
      },
      onComplete: () => {
        console.log('Streaming complete');
        isStreaming = false;
      }
    });
  }
</script>

<button on:click={startStreaming} disabled={isStreaming}>
  {isStreaming ? 'Streaming...' : 'Load Analytics Data'}
</button>

<div>Records loaded: {records.length}</div>
```

## Benefits

- **Automatic Detection**: FluidKit detects streaming responses and generates appropriate clients
- **Type Safety**: Streaming callbacks maintain full TypeScript type safety
- **Environment Aware**: Same streaming clients work in SSR and browser contexts
- **Performance Optimized**: Efficient streaming patterns for large data and real-time updates
- **Clean APIs**: Generated clients abstract streaming complexity while maintaining control

Streaming support enables building responsive, real-time applications with Python backends and SvelteKit frontends.
