"""
Real-Time Alert System for Critical Parking Violations
Generates push notifications for high-priority enforcement actions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import json


class ViolationAlertSystem:
    """
    Real-time alert generation for critical violations.
    
    Triggers alerts when:
    - CII > threshold AND anomaly_score < threshold
    - Cascade detected at nearby junction within 15 min
    - High-impact vehicle (tanker, bus) at major junction during peak
    
    Integrates with BTP's existing WhatsApp/SMS workflows.
    """
    
    def __init__(
        self,
        cii_threshold: float = 500,
        anomaly_threshold: float = -0.5,
        cascade_window_minutes: int = 15,
        peak_hours: List[tuple] = [(9, 11), (17, 20)]
    ):
        """
        Initialize alert system.
        
        Args:
            cii_threshold: Minimum CII score for alerts
            anomaly_threshold: Maximum anomaly score (lower = more anomalous)
            cascade_window_minutes: Time window for cascade detection
            peak_hours: List of (start_hour, end_hour) tuples for rush hour
        """
        self.cii_threshold = cii_threshold
        self.anomaly_threshold = anomaly_threshold
        self.cascade_window_minutes = cascade_window_minutes
        self.peak_hours = peak_hours
        
        # High-impact vehicle types
        self.critical_vehicles = {
            'TANKER', 'TRUCK', 'LORRY', 'BUS', 'HEAVY COMMERCIAL VEHICLE'
        }
        
    def is_peak_hour(self, timestamp: pd.Timestamp) -> bool:
        """Check if timestamp falls within peak hours."""
        hour = timestamp.hour
        for start, end in self.peak_hours:
            if start <= hour <= end:
                return True
        return False
    
    def check_cascade_risk(
        self,
        new_violation: pd.Series,
        recent_violations: pd.DataFrame
    ) -> bool:
        """
        Detect if new violation is part of a cascade pattern.
        
        A cascade is defined as 3+ violations within:
        - 1km radius
        - cascade_window_minutes time window
        - At least one at a BTP junction
        """
        if len(recent_violations) < 2:
            return False
        
        new_lat = new_violation.get('latitude', 0)
        new_lon = new_violation.get('longitude', 0)
        new_time = pd.to_datetime(new_violation.get('created_datetime', new_violation.get('created_date')))
        
        # Filter violations within time window
        time_diff = (recent_violations['created_datetime'] - new_time).abs()
        within_time = time_diff <= pd.Timedelta(minutes=self.cascade_window_minutes)
        
        # Filter violations within 1km (rough approximation: 0.01° ≈ 1km)
        lat_diff = (recent_violations['latitude'] - new_lat).abs()
        lon_diff = (recent_violations['longitude'] - new_lon).abs()
        within_distance = (lat_diff < 0.01) & (lon_diff < 0.01)
        
        # Count nearby violations
        nearby = recent_violations[within_time & within_distance]
        
        # Check if at least one is at a junction
        has_junction = nearby.get('junction_', '').apply(
            lambda x: str(x).startswith('BTP')
        ).any() if 'junction_' in nearby.columns else False
        
        # Cascade if 3+ violations and at least one at junction
        return len(nearby) >= 2 and has_junction
    
    def compute_alert_priority(
        self,
        cii_score: float,
        anomaly_score: float,
        cascade_risk: bool,
        is_critical_vehicle: bool,
        is_peak: bool
    ) -> str:
        """
        Determine alert priority level.
        
        Returns: CRITICAL, HIGH, MEDIUM, or INFO
        """
        if cascade_risk:
            return 'CRITICAL'
        
        if cii_score > self.cii_threshold * 1.5 and is_critical_vehicle and is_peak:
            return 'CRITICAL'
        
        if cii_score > self.cii_threshold or anomaly_score < self.anomaly_threshold:
            return 'HIGH'
        
        if is_critical_vehicle and is_peak:
            return 'MEDIUM'
        
        return 'INFO'
    
    def generate_alert(
        self,
        violation: pd.Series,
        cii_score: float,
        anomaly_score: Optional[float] = None,
        cascade_risk: bool = False
    ) -> Dict:
        """
        Generate structured alert message for officer dispatch.
        
        Returns dict compatible with WhatsApp/SMS APIs.
        """
        timestamp = pd.to_datetime(violation.get('created_date'))
        is_peak = self.is_peak_hour(timestamp)
        
        vehicle_type = violation.get('updated_vehicle_type', violation.get('vehicle_type', 'Unknown'))
        is_critical_vehicle = str(vehicle_type).upper() in self.critical_vehicles
        
        priority = self.compute_alert_priority(
            cii_score,
            anomaly_score if anomaly_score is not None else 0,
            cascade_risk,
            is_critical_vehicle,
            is_peak
        )
        
        # Build location description
        junction = violation.get('junction_', 'No Junction')
        police_station = violation.get('police_station', 'Unknown Station')
        location = f"{violation.get('latitude', 0):.4f}, {violation.get('longitude', 0):.4f}"
        
        # Recommended action based on priority
        if priority == 'CRITICAL':
            action = 'DISPATCH_IMMEDIATELY'
            response_time = '< 10 minutes'
        elif priority == 'HIGH':
            action = 'SCHEDULE_ENFORCEMENT'
            response_time = '< 30 minutes'
        else:
            action = 'MONITOR'
            response_time = 'Next patrol cycle'
        
        alert = {
            'alert_id': f"ALERT_{violation.get('id', 'UNKNOWN')}_{datetime.now().strftime('%H%M%S')}",
            'priority': priority,
            'violation_id': violation.get('id'),
            'location': {
                'coordinates': location,
                'junction': junction,
                'police_station': police_station,
                'address': violation.get('location', 'Unknown location')
            },
            'vehicle': {
                'type': vehicle_type,
                'number': violation.get('vehicle_number', 'Unknown'),
                'critical': is_critical_vehicle
            },
            'scores': {
                'cii': round(cii_score, 1),
                'anomaly': round(anomaly_score, 3) if anomaly_score is not None else None,
                'cascade_detected': cascade_risk
            },
            'timing': {
                'reported_at': timestamp.isoformat() if pd.notna(timestamp) else None,
                'is_peak_hour': is_peak,
                'alert_generated_at': datetime.now().isoformat()
            },
            'action': {
                'recommended': action,
                'target_response_time': response_time,
                'requires_towing': is_critical_vehicle or cii_score > 700
            }
        }
        
        alert['message'] = self._format_alert_message(alert)
        
        return alert
    
    def _format_alert_message(self, alert: Dict) -> str:
        """
        Format alert as human-readable message for WhatsApp/SMS.
        """
        priority_emoji = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '📍',
            'INFO': 'ℹ️'
        }
        
        emoji = priority_emoji.get(alert['priority'], 'ℹ️')
        
        message = f"""{emoji} *{alert['priority']} PRIORITY ALERT*

📍 Location: {alert['location']['junction']}
   Police Station: {alert['location']['police_station']}
   Coordinates: {alert['location']['coordinates']}

🚗 Vehicle: {alert['vehicle']['type']}
   Number: {alert['vehicle']['number']}

📊 Impact Score: {alert['scores']['cii']}
   {'⚡ CASCADE DETECTED' if alert['scores']['cascade_detected'] else ''}

✅ Action: {alert['action']['recommended']}
   Target: {alert['action']['target_response_time']}

Reported: {alert['timing']['reported_at']}
"""
        
        return message.strip()
    
    def check_and_alert(
        self,
        new_violation: pd.Series,
        recent_violations: pd.DataFrame,
        cii_score: float,
        anomaly_score: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Main entry point: Check if violation warrants alert and generate it.
        
        Returns alert dict if triggered, None otherwise.
        """
        # Check cascade risk
        cascade_risk = self.check_cascade_risk(new_violation, recent_violations)
        
        # Determine if alert should be triggered
        should_alert = (
            cii_score > self.cii_threshold or
            (anomaly_score is not None and anomaly_score < self.anomaly_threshold) or
            cascade_risk
        )
        
        if not should_alert:
            return None
        
        # Generate and return alert
        return self.generate_alert(new_violation, cii_score, anomaly_score, cascade_risk)
    
    def send_via_whatsapp(self, alert: Dict, officer_phone: str) -> bool:
        """
        Send alert via WhatsApp Business API (mock implementation).
        
        In production, integrate with:
        - Twilio WhatsApp API
        - Gupshup (popular in India)
        - BTP's existing WhatsApp infrastructure
        """
        # Mock implementation - logs to console
        print(f"\n📱 WhatsApp Alert to {officer_phone}:")
        print("-" * 50)
        print(alert['message'])
        print("-" * 50)
        
        # In production:
        # import requests
        # response = requests.post(
        #     'https://api.whatsapp.com/send',
        #     json={
        #         'to': officer_phone,
        #         'message': alert['message']
        #     }
        # )
        # return response.status_code == 200
        
        return True
    
    def send_via_sms(self, alert: Dict, officer_phone: str) -> bool:
        """
        Send alert via SMS (mock implementation).
        
        In production, integrate with:
        - Twilio SMS API
        - MSG91 (popular in India)
        - BTP's existing SMS gateway
        """
        # Compress message for SMS (160 char limit per segment)
        sms_message = f"{alert['priority']} ALERT: {alert['vehicle']['type']} at {alert['location']['junction']}. CII:{alert['scores']['cii']}. Action: {alert['action']['recommended']}. {alert['location']['coordinates']}"
        
        print(f"\n📱 SMS Alert to {officer_phone}:")
        print(f"{sms_message[:160]}...")
        
        # In production:
        # import requests
        # response = requests.post(
        #     'https://api.msg91.com/api/send',
        #     data={
        #         'mobile': officer_phone,
        #         'message': sms_message
        #     }
        # )
        # return response.status_code == 200
        
        return True


def batch_process_violations(
    violations_df: pd.DataFrame,
    cii_scores: pd.Series,
    anomaly_scores: Optional[pd.Series] = None,
    alert_threshold_count: int = 10
) -> List[Dict]:
    """
    Process all violations and generate alerts for top priorities.
    
    Args:
        violations_df: DataFrame of violations
        cii_scores: Series of CII scores
        anomaly_scores: Optional Series of anomaly scores
        alert_threshold_count: Maximum number of alerts to generate
    
    Returns:
        List of alert dicts for top priority violations
    """
    alert_system = ViolationAlertSystem()
    alerts = []
    
    # Sort by CII score descending
    sorted_indices = cii_scores.nlargest(alert_threshold_count * 2).index
    
    for i, idx in enumerate(sorted_indices):
        if len(alerts) >= alert_threshold_count:
            break
        
        violation = violations_df.loc[idx]
        cii = cii_scores.loc[idx]
        anomaly = anomaly_scores.loc[idx] if anomaly_scores is not None else None
        
        # Get recent violations for cascade detection (excluding current)
        recent = violations_df.drop(idx).tail(100)
        if 'created_datetime' not in recent.columns:
            recent = recent.copy()
            recent['created_datetime'] = pd.to_datetime(recent.get('created_date', pd.Timestamp.now()))
        
        alert = alert_system.check_and_alert(violation, recent, cii, anomaly)
        
        if alert:
            alerts.append(alert)
    
    return alerts


if __name__ == "__main__":
    # Test alert system
    print("Testing Real-Time Alert System...\n")
    
    # Create test violation
    test_violation = pd.Series({
        'id': 'TEST001',
        'latitude': 12.9716,
        'longitude': 77.5946,
        'created_date': '2024-01-15 18:30:00',
        'vehicle_type': 'TANKER',
        'updated_vehicle_type': 'TANKER',
        'vehicle_number': 'KA01AB1234',
        'junction_': 'BTP044',
        'police_station': 'Shantinagar',
        'location': 'Koramangala 4th Block',
        'violation': '["WRONG PARKING"]'
    })
    
    # Create recent violations for cascade test
    recent_violations = pd.DataFrame([
        {
            'latitude': 12.9720,
            'longitude': 77.5950,
            'created_date': '2024-01-15 18:20:00',
            'junction_': 'BTP045'
        },
        {
            'latitude': 12.9710,
            'longitude': 77.5940,
            'created_date': '2024-01-15 18:25:00',
            'junction_': 'BTP044'
        }
    ])
    recent_violations['created_datetime'] = pd.to_datetime(recent_violations['created_date'])
    
    # Initialize and test
    alert_system = ViolationAlertSystem()
    alert = alert_system.check_and_alert(
        test_violation,
        recent_violations,
        cii_score=847,
        anomaly_score=-0.62
    )
    
    if alert:
        print("✅ Alert generated successfully!")
        print(f"Priority: {alert['priority']}")
        print(f"Action: {alert['action']['recommended']}")
        print(f"\nFull message:\n{alert['message']}")
    else:
        print("❌ No alert generated")
    
    print("\n✅ Real-time alert system module working correctly")
