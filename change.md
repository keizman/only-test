
'''
  改动

  - 扩展 Poco 本地包
      - 文件：Poco/poco/proxy.py
      - 在 UIObjectProxy 类中新增方法：
      - def click_with_bias(self, dx_px=0, dy_px=0)
      - 说明：
        - 用法示例：
          - `poco(text="西语手机端720资源02").click_with_bias(dy_px=-5)` 上偏移 5px
          - `poco(resourceId="com.example:id/play").click_with_bias(dx_px=10)` 右偏移 10px
        - 参数：
          - `dx_px`: 横向像素偏移（正右负左）
          - `dy_px`: 纵向像素偏移（正下负上）
        - 实现：
          - 调用 `self.get_position()` 获得元素中心点的归一化坐标
          - 使用 `self.poco.get_screen_size()` 获取屏幕分辨率（失败时回退 1080x1920）
          - 将像素偏移换算为归一化偏移，加到中心点上并裁剪到 [0,1]
          - 最终调用 `self.poco.click([nx, ny])`

  - 直接链式调用
      - poco(text="西语手机端720资源02").click_with_bias(dy_px=-5)
      - poco(resourceId="com.mobile.brasiltvmobile:id/mPlayPauseIcon").click_with_bias(dx_px=8, dy_px=-6)

  如果你希望，我也可以在用例中把某些“中心点击”的地方替换为 .click_with_bias(...)，例如播放按钮在视频中心上方偏移一点来避免挡住控件。需要的话告诉我具体位置。

'''