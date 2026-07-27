/**
 * Transitional router boundary for the Pro v6 migration.
 *
 * Navigation is owned by Umi's global history. Route matching hooks remain
 * React Router-compatible until each module is moved to Umi file routes.
 */
export {
  Link,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
