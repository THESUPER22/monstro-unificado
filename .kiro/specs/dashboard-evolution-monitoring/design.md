# Design Document: Dashboard Evolution Monitoring

## Overview

This design document outlines theementation approach for integrating the evolutionary system with the Monstro trading dashboard. The integration will provide real-time monitoring of the evolutionary system's performance, parameters, and progress through a set of RESTful API endpoints and corresponding UI components in the dashboard.

The evolutionary system consists of three main components:
1. `SistemaEvolucaoAdaptativa` - Adapts filters based on performance metrics
2. `SistemaEvolucaoHibrido` - Combines level-based evolution with adaptive adjustments
3. `FiltrosEvolutivos` - Applies evolutionary filters to trading decisions

This integration will expose these systems' data and metrics through the dashboard, allowing traders to monitor how the AI model is evolving and adapting to market conditions.

## Architecture

The integration will follow a client-server architecture:

1. **Server-side Components**:
   - API endpoints in the existing Flask application within `monstro_unificado.py`
   - Data processing and aggregation functions for evolutionary metrics
   - Integration with the existing evolutionary systems

2. **Client-side Components**:
   - New dashboard sections for evolutionary system monitoring
   - Charts and visualizations for performance metrics
   - Parameter display and history tracking

## Components and Interfaces

### 1. API Endpoints

We will add the following RESTful API endpoints to the existing Flask application:

#### 1.1 Evolution Metrics API

```python
@app.route("/api/evolution/metrics", methods=["GET"])
def api_evolution_metrics():
    """Return evolution metrics including performance trends."""
    try:
        # Get data from evolution systems
        metrics = {
            "performance": get_evolution_performance_metrics(),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(metrics)
    except Exception as e:
        logging.error(f"Error in evolution metrics API: {e}")
        return jsonify({"error": str(e)}), 500
```

#### 1.2 Evolution Parameters API

```python
@app.route("/api/evolution/parameters", methods=["GET"])
def api_evolution_parameters():
    """Return current evolutionary parameters and their history."""
    try:
        # Get parameters from evolution systems
        parameters = {
            "current": get_current_evolution_parameters(),
            "history": get_evolution_parameters_history(),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(parameters)
    except Exception as e:
        logging.error(f"Error in evolution parameters API: {e}")
        return jsonify({"error": str(e)}), 500
```

#### 1.3 Evolution Impact API

```python
@app.route("/api/evolution/impact", methods=["GET"])
def api_evolution_impact():
    """Return data about how evolution has impacted trading decisions."""
    try:
        # Get impact data
        impact = {
            "trading_performance": get_evolution_trading_impact(),
            "significant_events": get_evolution_significant_events(),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(impact)
    except Exception as e:
        logging.error(f"Error in evolution impact API: {e}")
        return jsonify({"error": str(e)}), 500
```

#### 1.4 Evolution Status API

```python
@app.route("/api/evolution/status", methods=["GET"])
def api_evolution_status():
    """Return overall status of the evolutionary systems."""
    try:
        # Get status from all evolutionary systems
        status = {
            "adaptative": get_adaptative_system_status(),
            "hybrid": get_hybrid_system_status(),
            "filters": get_filters_system_status(),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error in evolution status API: {e}")
        return jsonify({"error": str(e)}), 500
```

#### 1.5 Evolution Alerts API

```python
@app.route("/api/evolution/alerts", methods=["GET"])
def api_evolution_alerts():
    """Return recent alerts from the evolutionary systems."""
    try:
        # Get recent alerts
        alerts = {
            "recent": get_recent_evolution_alerts(),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(alerts)
    except Exception as e:
        logging.error(f"Error in evolution alerts API: {e}")
        return jsonify({"error": str(e)}), 500
```

### 2. Data Processing Functions

These functions will extract and process data from the evolutionary systems:

#### 2.1 Performance Metrics

```python
def get_evolution_performance_metrics():
    """Extract performance metrics from evolutionary systems."""
    metrics = {
        "reward_trend": extract_reward_trend(),
        "win_rate": extract_win_rate_trend(),
        "model_accuracy": extract_model_accuracy_trend(),
        "periods": {
            "daily": aggregate_metrics_by_period("daily"),
            "weekly": aggregate_metrics_by_period("weekly"),
            "monthly": aggregate_metrics_by_period("monthly")
        }
    }
    return metrics
```

#### 2.2 Parameter Tracking

```python
def get_current_evolution_parameters():
    """Get current parameters from all evolutionary systems."""
    parameters = {}

    # Get parameters from adaptive system
    if SISTEMA_EVOLUTIVO_DISPONIVEL and 'sistema_adaptativo' in globals():
        parameters["adaptive"] = sistema_adaptativo.filtros_atuais

    # Get parameters from hybrid system
    if SISTEMA_EVOLUTIVO_DISPONIVEL and 'sistema_hibrido' in globals():
        parameters["hybrid"] = sistema_hibrido.obter_filtros_finais()

    # Get parameters from filters system
    if SISTEMA_EVOLUTIVO_DISPONIVEL and 'filtros_evolutivos' in globals():
        parameters["filters"] = filtros_evolutivos.get_filtros_atuais()

    return parameters
```

#### 2.3 Impact Analysis

```python
def get_evolution_trading_impact():
    """Analyze how evolution has impacted trading performance."""
    # Read historical data
    df = pd.read_csv(HISTORICO_CSV)

    # Group by evolution cycles and calculate metrics
    # This is a simplified example - actual implementation would be more complex
    impact = {
        "before_after": calculate_before_after_metrics(),
        "by_evolution_cycle": calculate_metrics_by_cycle()
    }

    return impact
```

### 3. Integration with Evolutionary Systems

We'll create integration functions to connect the existing evolutionary systems with the dashboard:

```python
def initialize_evolution_monitoring():
    """Initialize monitoring for evolutionary systems."""
    global evolution_monitoring_active

    try:
        # Set up monitoring
        evolution_monitoring_active = True

        # Initialize storage for evolution events
        global evolution_events
        evolution_events = []

        # Set up alert system
        initialize_evolution_alerts()

        logging.info("✅ Evolution monitoring initialized")
    except Exception as e:
        logging.error(f"❌ Error initializing evolution monitoring: {e}")
        evolution_monitoring_active = False
```

### 4. Dashboard UI Components

The dashboard will include the following new UI components:

1. **Evolution Performance Chart**
   - Line chart showing reward trend, win rate, and model accuracy over time
   - Time period selector (daily, weekly, monthly)

2. **Parameters Panel**
   - Current values of key evolutionary parameters
   - History of parameter changes with timestamps
   - Visual indicators for parameter changes

3. **Trading Impact Section**
   - Before/after comparison of trading performance
   - Timeline of significant evolutionary events
   - Correlation between model improvements and trading results

4. **Alerts Panel**
   - Recent alerts from the evolutionary systems
   - Severity indicators and timestamps
   - Notification settings

## Data Models

### Evolution Metrics Model

```json
{
  "performance": {
    "reward_trend": [
      {"timestamp": "2025-07-15T10:30:00", "value": 0.75},
      {"timestamp": "2025-07-15T11:30:00", "value": 0.78}
    ],
    "win_rate": [
      {"timestamp": "2025-07-15T10:30:00", "value": 0.65},
      {"timestamp": "2025-07-15T11:30:00", "value": 0.67}
    ],
    "model_accuracy": [
      {"timestamp": "2025-07-15T10:30:00", "value": 0.72},
      {"timestamp": "2025-07-15T11:30:00", "value": 0.74}
    ],
    "periods": {
      "daily": {
        "average_reward": 0.76,
        "average_win_rate": 0.66,
        "average_accuracy": 0.73
      },
      "weekly": {
        "average_reward": 0.74,
        "average_win_rate": 0.64,
        "average_accuracy": 0.71
      },
      "monthly": {
        "average_reward": 0.72,
        "average_win_rate": 0.62,
        "average_accuracy": 0.70
      }
    }
  },
  "timestamp": "2025-07-16T12:30:00"
}
```

### Evolution Parameters Model

```json
{
  "current": {
    "adaptive": {
      "threshold_confianca": 0.65,
      "min_entropia_book": 0.4,
      "max_spread": 2.0,
      "min_volume_book": 250
    },
    "hybrid": {
      "threshold_confianca": 0.70,
      "min_entropia": 0.5,
      "max_spread": 1.5,
      "min_volume_book": 300,
      "cooldown_segundos": 60
    },
    "filters": {
      "threshold_confianca": 0.68,
      "min_entropia": 0.45,
      "max_spread": 1.8,
      "min_volume_book": 280
    }
  },
  "history": [
    {
      "timestamp": "2025-07-15T10:00:00",
      "parameter": "threshold_confianca",
      "old_value": 0.60,
      "new_value": 0.65,
      "system": "adaptive",
      "reason": "Low win rate"
    },
    {
      "timestamp": "2025-07-15T14:30:00",
      "parameter": "min_volume_book",
      "old_value": 200,
      "new_value": 250,
      "system": "adaptive",
      "reason": "Increasing selectivity"
    }
  ],
  "timestamp": "2025-07-16T12:30:00"
}
```

### Evolution Impact Model

```json
{
  "trading_performance": {
    "before_after": {
      "before": {
        "win_rate": 0.60,
        "profit_factor": 1.5,
        "average_profit": 15.0
      },
      "after": {
        "win_rate": 0.68,
        "profit_factor": 1.8,
        "average_profit": 18.5
      },
      "improvement": {
        "win_rate": "+13.3%",
        "profit_factor": "+20.0%",
        "average_profit": "+23.3%"
      }
    },
    "by_evolution_cycle": [
      {
        "cycle": 1,
        "win_rate": 0.62,
        "profit_factor": 1.6,
        "average_profit": 16.0
      },
      {
        "cycle": 2,
        "win_rate": 0.65,
        "profit_factor": 1.7,
        "average_profit": 17.2
      }
    ]
  },
  "significant_events": [
    {
      "timestamp": "2025-07-15T09:45:00",
      "event": "Level Up",
      "description": "System evolved from 'iniciante' to 'intermediario'",
      "impact": "Increased selectivity, higher threshold"
    },
    {
      "timestamp": "2025-07-15T14:20:00",
      "event": "Parameter Adjustment",
      "description": "Threshold increased from 0.60 to 0.65",
      "impact": "Win rate improved by 5%"
    }
  ],
  "timestamp": "2025-07-16T12:30:00"
}
```

## Error Handling

The integration will implement comprehensive error handling:

1. **API Error Handling**
   - All API endpoints will catch exceptions and return appropriate error responses
   - Errors will be logged with detailed information
   - Client will receive meaningful error messages

2. **Data Validation**
   - Input data will be validated before processing
   - Missing or invalid data will be handled gracefully
   - Default values will be provided when necessary

3. **System Availability**
   - The dashboard will check if evolutionary systems are available
   - Appropriate messages will be displayed if systems are not available
   - Partial functionality will be maintained when possible

4. **Recovery Mechanisms**
   - Automatic retry for transient failures
   - Fallback to cached data when real-time data is unavailable
   - Periodic refresh to recover from temporary issues

## Testing Strategy

### Unit Testing

1. **API Endpoint Tests**
   - Test each API endpoint with valid and invalid inputs
   - Verify correct response formats and status codes
   - Test error handling and edge cases

2. **Data Processing Tests**
   - Test data extraction and aggregation functions
   - Verify calculations and transformations
   - Test with various data scenarios

3. **Integration Tests**
   - Test interaction between API and evolutionary systems
   - Verify data flow and consistency
   - Test system behavior with simulated evolution events

### End-to-End Testing

1. **Dashboard Functionality**
   - Test dashboard rendering and updates
   - Verify chart and visualization accuracy
   - Test user interactions and controls

2. **Performance Testing**
   - Test API response times under load
   - Verify dashboard performance with large datasets
   - Test concurrent user scenarios

3. **Compatibility Testing**
   - Test across different browsers and devices
   - Verify responsive design and layout
   - Test with different screen sizes and resolutions

## Implementation Plan

The implementation will be divided into the following phases:

1. **Phase 1: API Development**
   - Implement core API endpoints
   - Create data processing functions
   - Integrate with evolutionary systems

2. **Phase 2: Dashboard UI**
   - Develop performance charts and visualizations
   - Create parameter display components
   - Implement trading impact section

3. **Phase 3: Alert System**
   - Develop alert generation logic
   - Create alert display components
   - Implement notification system

4. **Phase 4: Testing and Refinement**
   - Conduct comprehensive testing
   - Optimize performance
   - Refine user experience

Each phase will include appropriate testing and validation to ensure quality and reliability.
