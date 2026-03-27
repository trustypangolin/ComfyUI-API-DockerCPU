# Plan: Enhance `audio_to_base64()` Function

## Function Overview
**Function Name**: `audio_to_base64()` and `_audio_to_base64()`
**Current Location**: 
- `common/utils.py` (lines 65-104) - Already exists
- `API/FalAi/node.py` (lines 126-148) - Duplicate
- `API/Replicate/node.py` (lines 165-185) - Duplicate

**Target Location**: `common/utils.py` (enhance existing)

## Current Implementations (~80% Similar)

### common/utils.py (Existing)
```python
def audio_to_base64(
    audio: Union[tuple, dict], 
    format: str = "wav"
) -> str:
    """Convert audio data to a base64 encoded data URI."""
    if isinstance(audio, dict):
        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate")
    else:
        waveform, sample_rate = audio
    
    # Ensure waveform is 2D
    if isinstance(waveform, torch.Tensor):
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        elif waveform.dim() > 2:
            waveform = waveform.squeeze()
            if waveform.dim() > 2:
                raise ValueError("Waveform must be 1D or 2D")
        waveform_np = waveform.numpy().T
    else:
        waveform_np = waveform
        if waveform_np.ndim == 1:
            waveform_np = waveform_np.reshape(1, -1)
    
    buffer = io.BytesIO()
    sf.write(buffer, waveform_np, sample_rate, format=format)
    buffer.seek(0)
    audio_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:audio/{format};base64,{audio_str}"
```

### API/FalAi/node.py (Duplicate)
```python
def _audio_to_base64(self, audio):
    """Convert audio tensor to base64 data URI."""
    import base64
    import soundfile as sf
    
    if isinstance(audio, dict):
        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate")
    else:
        waveform, sample_rate = audio

    if isinstance(waveform, torch.Tensor):
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        waveform_np = waveform.numpy().T
    else:
        waveform_np = waveform

    buffer = BytesIO()
    sf.write(buffer, waveform_np, sample_rate, format="wav")
    buffer.seek(0)
    audio_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:audio/wav;base64,{audio_str}"
```

### API/Replicate/node.py (Duplicate)
```python
def _audio_to_base64(self, audio):
    """Convert audio tensor to base64 data URI."""
    if isinstance(audio, dict):
        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate")
    else:
        waveform, sample_rate = audio

    if isinstance(waveform, torch.Tensor):
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        waveform_np = waveform.numpy().T
    else:
        waveform_np = waveform

    buffer = BytesIO()
    import soundfile as sf
    sf.write(buffer, waveform_np, sample_rate, format="wav")
    buffer.seek(0)
    audio_str = base64_encode(buffer.getvalue()).decode()
    return f"data:audio/wav;base64,{audio_str}"
```

## Why Extract
- **Duplication Level**: ~80% similar (minor differences in error handling)
- **Risk Level**: Low
- **Impact**: High (used in all audio processing)
- **Lines Saved**: ~60 lines (30 lines × 2 files)

## Implementation Steps

### Step 1: Enhance `common/utils.py`
The existing `audio_to_base64()` function is already good. Just ensure it handles all edge cases:

```python
def audio_to_base64(
    audio: Union[tuple, dict], 
    format: str = "wav"
) -> str:
    """
    Convert audio data to a base64 encoded data URI.
    
    Handles various input formats:
    - Dict with 'waveform' and 'sample_rate' keys
    - Tuple of (waveform, sample_rate)
    - Waveform as 1D or 2D tensor
    - Waveform as numpy array
    
    Args:
        audio: Either a tuple of (waveform, sample_rate) or a dict with 
               'waveform' and 'sample_rate' keys
        format: Audio format (wav, mp3, etc.)
        
    Returns:
        Base64 encoded data URI string (data:audio/wav;base64,...)
        
    Examples:
        >>> # From dict
        >>> audio = {"waveform": torch.rand(1, 44100), "sample_rate": 44100}
        >>> data_uri = audio_to_base64(audio)
        >>> data_uri.startswith("data:audio/wav;base64,")
        True
        
        >>> # From tuple
        >>> audio = (torch.rand(1, 44100), 44100)
        >>> data_uri = audio_to_base64(audio)
        >>> data_uri.startswith("data:audio/wav;base64,")
        True
    """
    if isinstance(audio, dict):
        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate")
    else:
        waveform, sample_rate = audio
    
    # Ensure waveform is 2D
    if isinstance(waveform, torch.Tensor):
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        elif waveform.dim() > 2:
            waveform = waveform.squeeze()
            if waveform.dim() > 2:
                raise ValueError("Waveform must be 1D or 2D")
        waveform_np = waveform.numpy().T
    else:
        waveform_np = waveform
        if waveform_np.ndim == 1:
            waveform_np = waveform_np.reshape(1, -1)
    
    buffer = io.BytesIO()
    sf.write(buffer, waveform_np, sample_rate, format=format)
    buffer.seek(0)
    audio_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:audio/{format};base64,{audio_str}"
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `_audio_to_base64()` method definition (lines 126-148)
- Add import: `from common.utils import audio_to_base64`
- Update method to call the common function:
  ```python
  def _audio_to_base64(self, audio):
      """Convert audio tensor to base64 data URI."""
      return audio_to_base64(audio, format="wav")
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `_audio_to_base64()` method definition (lines 165-185)
- Add import: `from common.utils import audio_to_base64`
- Update method to call the common function:
  ```python
  def _audio_to_base64(self, audio):
      """Convert audio tensor to base64 data URI."""
      return audio_to_base64(audio, format="wav")
  ```

## Testing Checklist

- [ ] Verify function handles dict input with waveform and sample_rate
- [ ] Verify function handles tuple input with waveform and sample_rate
- [ ] Verify function handles 1D waveform tensor
- [ ] Verify function handles 2D waveform tensor
- [ ] Verify function handles numpy array waveform
- [ ] Verify function preserves sample rate correctly
- [ ] Verify function returns correct base64 data URI format
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `soundfile`, `base64`, `io`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
