# Plan: Extract `handle_audio_output()` Function

## Function Overview
**Function Name**: `handle_audio_output()`
**Current Location**: 
- `API/FalAi/node.py` (lines 197-218)
- `API/Replicate/node.py` (lines 257-278)

**Target Location**: `common/output_handlers.py`

## Current Implementation (100% Identical)

```python
def handle_audio_output(self, output):
    """Process audio output from API."""
    if output is None:
        return None

    output_list = output if isinstance(output, list) else [output]
    audio_data = []
    
    for audio_file in output_list:
        if audio_file:
            audio_content = BytesIO(audio_file.read())
            waveform, sample_rate = torchaudio.load(audio_content)
            audio_data.append({
                "waveform": waveform.unsqueeze(0),
                "sample_rate": sample_rate
            })

    if len(audio_data) == 1:
        return audio_data[0]
    elif len(audio_data) > 0:
        return audio_data
    return None
```

## Why Extract
- **Duplication Level**: 100% identical in FalAi & Replicate
- **Risk Level**: Low
- **Impact**: High (used in all audio model outputs)
- **Lines Saved**: ~60 lines (30 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/output_handlers.py`
Add the function to the existing file:

```python
def handle_audio_output(output) -> Optional[Union[Dict, List[Dict]]]:
    """
    Process audio output from API.
    
    Converts file-like objects or lists of file-like objects to audio data.
    
    Args:
        output: Single file-like object or list of file-like objects
                containing audio data
                
    Returns:
        Dict with 'waveform' (tensor) and 'sample_rate' (int) for single audio,
        List of dicts for multiple audio files, or None if output is empty
        
    Examples:
        >>> # Single audio file
        >>> audio_data = handle_audio_output(file_obj)
        >>> audio_data['waveform'].shape
        torch.Size([1, 1, 44100])
        >>> audio_data['sample_rate']
        44100
        
        >>> # Multiple audio files
        >>> audio_data = handle_audio_output([file_obj1, file_obj2])
        >>> len(audio_data)
        2
    """
    if output is None:
        return None

    output_list = output if isinstance(output, list) else [output]
    audio_data = []
    
    for audio_file in output_list:
        if audio_file:
            audio_content = BytesIO(audio_file.read())
            waveform, sample_rate = torchaudio.load(audio_content)
            audio_data.append({
                "waveform": waveform.unsqueeze(0),
                "sample_rate": sample_rate
            })

    if len(audio_data) == 1:
        return audio_data[0]
    elif len(audio_data) > 0:
        return audio_data
    return None
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `handle_audio_output()` method definition (lines 197-218)
- Add import: `from common.output_handlers import handle_audio_output`
- Update method to call the common function:
  ```python
  def handle_audio_output(self, output):
      """Process audio output from API."""
      return handle_audio_output(output)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `handle_audio_output()` method definition (lines 257-278)
- Add import: `from common.output_handlers import handle_audio_output`
- Update method to call the common function:
  ```python
  def handle_audio_output(self, output):
      """Process audio output from API."""
      return handle_audio_output(output)
  ```

## Testing Checklist

- [x] Verify function handles None output correctly
- [x] Verify function handles single audio file object
- [x] Verify function handles list of audio file objects
- [x] Verify function returns correct dict structure for single audio
- [x] Verify function returns correct list structure for multiple audio
- [x] Verify waveform tensor has correct shape (1, channels, samples)
- [x] Verify sample_rate is preserved correctly
- [x] Test with FalAi API
- [x] Test with Replicate API
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `torchaudio`, `BytesIO`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
