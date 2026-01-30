(function() {
    // 默认后端地址，部署后可在页面手动修改并保存在 localStorage 中
    var default_api = window.location.origin.includes('vercel.app') ? 'https://your-backend-api.com' : '';
    
    window.API_BASE_URL = localStorage.getItem('CL_BACKEND_URL') || default_api;
    
    console.log("Current Backend API URL: ", window.API_BASE_URL);

    // 提供一个全局方法修改后端地址
    window.setBackendUrl = function(url) {
        if (url.endsWith('/')) url = url.slice(0, -1);
        localStorage.setItem('CL_BACKEND_URL', url);
        window.API_BASE_URL = url;
        layer.msg('后端地址已更新，即将刷新页面');
        setTimeout(function() { location.reload(); }, 1500);
    };
})();
