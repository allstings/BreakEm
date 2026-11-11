# Breakout Power-Up Enhancement Planning

## Project Overview
The goal of this project is to enhance the existing "Breakout" game by adding support for two types of power-ups:
1. **Time limited**: Lasts for a defined duration (in seconds) once obtained.
2. **Session limited**: Lasts until the ball is lost and the game resets to its normal state.

## Current State
- The game is implemented in `breakout.py` using `pygame`.
- It already supports a "wide" power-up (Time limited) and a "multi" power-up (instant).
- The `PowerUp` class handles the falling and catching logic.
- The `Game` class handles the effects of caught power-ups in `on_powerup_caught`.

## Proposed Enhancements

### 1. Time Limited Power-ups
- **Boost**: 
    - Effect: Increases the speed of all current balls by 50%.
    - Duration: 5 seconds.

- **Slow**:
    - Effect: Decreases the speed of all current balls by 50%.
    - Duration: 5 seconds.

## Technical Tasks

### Phase 1: Analysis & Preparation
- [ ] Review `breakout.py` to identify the best locations for new variables and logic.
- [ ] Identify how to cleanly handle the `speed_boost` and `speed_reduce` timer to avoid conflicts with brick hits.

### Phase 2: Implementation
- [ ] Update `PowerUp.TYPES` to include `FAST` and `SLOW`.
- [ ] Modify `Game.on_powerup_caught` to handle the new power-up types.
- [ ] Update `Game.serve` to reset session-limited flags.
- [ ] Implement the `speed_boost` and `speed_reduce` timers logic in `Game.update`.

### Phase 3: Testing & Refinement
- [ ] Verify that "Boost" correctly applies to all balls and expires after 5 seconds.
- [ ] Verify that "Slow" correctly applies to all balls and expires after 5 seconds.
- [ ] Ensure no regressions in existing power-up behaviors (Wide and Multi).
