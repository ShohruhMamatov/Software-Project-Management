import useAuthBlob from "./useAuthBlob";

export default function AuthImage({ path, alt, fallback = "No image", ...props }) {
  const { url, failed } = useAuthBlob(path);
  if (url) return <img src={url} alt={alt} {...props} />;
  return <div className="img-placeholder">{failed ? fallback : "Loading…"}</div>;
}
