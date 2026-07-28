import { Navigate } from "react-router";

export default function ProcurementIndex(): React.JSX.Element {
  return <Navigate to="/procurement/dashboard" replace />;
}
