interface LocationTooltipTextProps {
  name: string;
  aircraft_present: number;
  ground_units: number;
  max_deployable_ground_units: number;
  front_line_stances: string[];
}

export const LocationTooltipText = (props: LocationTooltipTextProps) => {
  var front_line_stances = props.front_line_stances.length > 0 ? (
    <div>
      <p style={{ margin: 0 }}>Front Line Stances:</p>
      <ul style={{ margin: 0 }}>{props.front_line_stances.map((stance) => <li>{stance}</li>)}</ul>
    </div>
  ) : null;

  return (
    <div>
      <h3 style={{ margin: 0 }}>{props.name}</h3>
      <p style={{ margin: 0 }}>Aircraft Present: {props.aircraft_present}</p>
      <p style={{ margin: 0 }}>Ground Units: {props.ground_units}</p>
      <p style={{ margin: 0 }}>Max Deployable Ground Units: {props.max_deployable_ground_units}</p>
      {front_line_stances}
    </div>
  )
};

export default LocationTooltipText;
