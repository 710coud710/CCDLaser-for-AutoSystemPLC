# Testing Checklist - Dual CCD System

## Pre-Test Setup

- [ ] Đảm bảo 2 cameras được cắm vào
- [ ] Check `setting/camera.yaml`:
  - [ ] `camera_ccd1.ip = "0"`
  - [ ] `camera_ccd2.ip = "1"`
  - [ ] `mono_mode` đã set đúng (1 hoặc 0)
- [ ] Python environment có đủ dependencies
- [ ] MindVision SDK đã cài đặt

## Phase 1: Basic Startup

### Test 1.1: Application Launch
- [ ] Run `python main_dual_ccd.py`
- [ ] Application window xuất hiện
- [ ] 2 panels hiển thị (CCD1 trái, CCD2 phải)
- [ ] Status: "CCD1: Not started", "CCD2: Not started"
- [ ] Buttons: Start enabled, Stop disabled

### Test 1.2: Window Layout
- [ ] CCD1 panel bên trái
- [ ] CCD2 panel bên phải
- [ ] Image display areas visible
- [ ] Control buttons visible
- [ ] Status text areas visible

## Phase 2: CCD1 Testing (Độc Lập)

### Test 2.1: Start CCD1
- [ ] Click "Start CCD1"
- [ ] Status changes to "Connecting..."
- [ ] Status changes to "Connected"
- [ ] Status changes to "Streaming"
- [ ] Button states: Start disabled, Stop enabled
- [ ] Logs xuất hiện trong status text area
- [ ] `[CCD1]` prefix trong logs

### Test 2.2: CCD1 Frame Display
- [ ] Frames hiển thị trong CCD1 image display
- [ ] Frame rate smooth (~30 FPS)
- [ ] Image không bị flicker
- [ ] Mono/RGB đúng theo config

### Test 2.3: Stop CCD1
- [ ] Click "Stop CCD1"
- [ ] Streaming stops
- [ ] Status changes to "Not started"
- [ ] Button states: Start enabled, Stop disabled
- [ ] No errors in logs

### Test 2.4: Restart CCD1
- [ ] Click "Start CCD1" again
- [ ] Camera reconnects successfully
- [ ] Streaming resumes normally

## Phase 3: CCD2 Testing (Độc Lập)

### Test 3.1: Start CCD2
- [ ] Click "Start CCD2"
- [ ] Status changes to "Connecting..."
- [ ] Status changes to "Connected"
- [ ] Status changes to "Streaming"
- [ ] Button states: Start disabled, Stop enabled
- [ ] Logs xuất hiện với `[CCD2]` prefix

### Test 3.2: CCD2 Frame Display
- [ ] Frames hiển thị trong CCD2 image display
- [ ] Frame rate smooth (~30 FPS)
- [ ] Image không bị flicker
- [ ] Mono/RGB đúng theo config

### Test 3.3: Stop CCD2
- [ ] Click "Stop CCD2"
- [ ] Streaming stops
- [ ] Status changes to "Not started"
- [ ] Button states: Start enabled, Stop disabled
- [ ] No errors in logs

### Test 3.4: Restart CCD2
- [ ] Click "Start CCD2" again
- [ ] Camera reconnects successfully
- [ ] Streaming resumes normally

## Phase 4: Concurrent Testing (Cả 2 CCD Cùng Lúc)

### Test 4.1: Start Both CCDs
- [ ] Start CCD1 first
- [ ] CCD1 streaming OK
- [ ] Start CCD2
- [ ] CCD2 streaming OK
- [ ] Both cameras streaming simultaneously
- [ ] Both frame rates smooth
- [ ] No interference between cameras

### Test 4.2: Independent Operation
- [ ] CCD1 đang stream, CCD2 idle → OK
- [ ] CCD2 đang stream, CCD1 idle → OK
- [ ] Both streaming → OK
- [ ] Stop CCD1 → CCD2 vẫn stream OK
- [ ] Stop CCD2 → CCD1 vẫn stream OK

### Test 4.3: Performance
- [ ] CPU usage acceptable (< 50%)
- [ ] Memory usage stable
- [ ] No frame drops
- [ ] No lag in UI

## Phase 5: Error Handling

### Test 5.1: Missing Camera
- [ ] Disconnect CCD1 camera physically
- [ ] Start CCD1 → Error displayed
- [ ] Start CCD2 → CCD2 vẫn hoạt động OK
- [ ] CCD2 không bị ảnh hưởng

### Test 5.2: Camera Disconnect During Streaming
- [ ] Start both CCDs
- [ ] Unplug CCD1 cable
- [ ] CCD1 shows error
- [ ] CCD2 vẫn streaming OK
- [ ] No crash

### Test 5.3: Wrong Camera Index
- [ ] Set `camera_ccd1.ip = "5"` (invalid)
- [ ] Start CCD1 → Error: "Camera index out of range"
- [ ] Error handled gracefully
- [ ] No crash

### Test 5.4: Rapid Start/Stop
- [ ] Start CCD1 → Stop CCD1 (nhanh)
- [ ] Repeat 5 lần
- [ ] No hang
- [ ] No crash
- [ ] No resource leak

## Phase 6: Configuration Testing

### Test 6.1: Mono Mode
- [ ] Set `mono_mode: 1` for both CCDs
- [ ] Start → Images grayscale
- [ ] Change to `mono_mode: 0`
- [ ] Restart → Images RGB

### Test 6.2: Exposure Settings
- [ ] Set different `exposure_time` for CCD1 và CCD2
- [ ] Start both
- [ ] Brightness khác nhau (đúng config)

### Test 6.3: Flip Horizontal
- [ ] Set `flip_horizontal: true` for CCD1
- [ ] Set `flip_horizontal: false` for CCD2
- [ ] Start → CCD1 mirrored, CCD2 not mirrored

## Phase 7: Thread Safety

### Test 7.1: Thread Independence
- [ ] Start CCD1 → 1 thread spawned
- [ ] Start CCD2 → 2nd thread spawned
- [ ] Both threads running independently
- [ ] Check thread IDs in logs (different)

### Test 7.2: No Deadlock
- [ ] Start both CCDs
- [ ] Rapid stop/start alternating
- [ ] No freeze
- [ ] No deadlock

### Test 7.3: Clean Shutdown
- [ ] Start both CCDs
- [ ] Close main window
- [ ] Both threads terminate cleanly
- [ ] No "thread still running" warnings
- [ ] Camera resources released

## Phase 8: Long Running Test

### Test 8.1: Stability
- [ ] Start both CCDs
- [ ] Let run for 30 minutes
- [ ] No frame drops
- [ ] No memory leak
- [ ] No crashes

### Test 8.2: Memory
- [ ] Monitor memory before start
- [ ] Run for 30 minutes
- [ ] Check memory after
- [ ] Memory increase < 10%

## Phase 9: Regression Testing (Old System)

### Test 9.1: Old System Still Works
- [ ] Run `python main.py`
- [ ] Old system launches OK
- [ ] Single camera works
- [ ] No conflicts with new system

### Test 9.2: Backward Compatibility
- [ ] Old `camera` config key still supported
- [ ] Old `pixel_format` still works
- [ ] No breaking changes for existing users

## Phase 10: Documentation

### Test 10.1: Quick Start Guide
- [ ] Follow `DUAL_CCD_QUICKSTART.md`
- [ ] All steps work as described
- [ ] Screenshots accurate (if any)

### Test 10.2: Architecture Doc
- [ ] Read `docs/dual-ccd-architecture.md`
- [ ] Diagram matches implementation
- [ ] Code examples work

### Test 10.3: Migration Summary
- [ ] Read `MIGRATION_SUMMARY.md`
- [ ] File counts accurate
- [ ] Instructions clear

## Test Summary

### Passed: _____ / _____
### Failed: _____ / _____

### Critical Issues:
- 

### Non-Critical Issues:
- 

### Notes:
- 

---

## Sign-off

Tester: _____________________
Date: _____________________
Version: _____________________

✅ System Ready for Production
❌ System Needs Fixes
