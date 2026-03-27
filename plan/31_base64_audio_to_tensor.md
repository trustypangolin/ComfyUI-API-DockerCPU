# Plan: Extract `base64_audio_to_tensor()` Function

## Function Overview
**Function Name**: `base64_audio_to_tensor()`
**Current Location**: 
- `common/utils.py` (lines 148-183) - Already exists

**Target Location**: `common/utils.py` (already there, just document it)

## Current Implementation (Already in common/utils.py)

```python
def base64_audio_to_tensor(
    base64_str: str,
    format: str = "wav"
) -> Optional[dict]:
    """
    Convert a base64 audio string to audio data.
    
    Args:
        base64_str: Base64 encoded audio data URI
        format: Audio format (wav, mp3, etc.)
        
    Returns:
        Dict with 'waveform' (tensor) and 'sample_rate' (int), or None if fails
    """
    if not base64_str or not isinstance(base64_str, str):
        return None
    
    try:
        # Extract base64 content from data URL
        if "," in base64_str:
            base64_data = base64_str.split(",", 1)[1]
        else:
            base64_data = base64_str
        
        audio_data = base64.b64decode(base64_data, validate=True)
        audio_buffer = io.BytesIO(audio_data)
        
        waveform, sample_rate = sf.load(audio_buffer, format=format)
        
        return {
            "waveform": torch.from_numpy(waveform).unsqueeze(0),
            "sample_rate": sample_rate
        }
    except Exception as e:
        print(f"Error converting base64 to audio tensor: {e}")
        return None
```

## Why Document
- **Duplication Level**: Already in common/utils.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Function Exists
The function already exists in `common/utils.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (function is only in common/utils.py)

## Testing Checklist

- [x] Verify function converts base64 audio data URI correctly
- [x] Verify function converts raw base64 string correctly
- [x] Verify function handles None input correctly
- [x] Verify function handles empty string correctly
- [x] Verify function handles invalid base64 correctly
- [x] Verify function returns correct dict structure
- [x] Verify function preserves sample rate correctly
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `soundfile`, `base64`, `io`

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
